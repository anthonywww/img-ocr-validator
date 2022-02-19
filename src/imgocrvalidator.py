import os
import io
import re
import sys
import json
import time
import hashlib
import requests
import requests.exceptions
import enchant
import argparse
import tempfile
import pytesseract
from urllib.error import *
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from PIL import Image

from severity import Severity

class ImgOCRValidator():

	def __init__(self, urls: str, options: dict):
		
		# Check if only generating HTML report from existing report.json
		if options["parse_only"]:
			try:
				fp = open("report.json", 'r')
				json_report = json.loads(fp.read())
				fp.close()
				self.generate_report(json_report)
			except Exception as err:
				self.log(f"Error while trying to read report.json file: {err}")
			return
				
		# Check if URLs are valid
		for url in urls:
			if not self.uri_validator(url):
				print(f"Invalid URL provided: {url}")
				return
		
		if len(urls) == 0:
			raise Exception("No URLs provided")
		
		self.results = {}
		self.parse(urls, options)
		
		if options["generate_report"]:
			self.generate_report(self.results)

	def generate_report(self, results):
		self.log(f"Saving html report ...")
		
		try:
			fp = open("src/template.html", 'r')
			original_template = fp.read()
			fp.close()
			
			# Create reports/ directory
			if not os.path.isdir("reports"):
				os.mkdir("reports")
			
			for result in results:
				
				report_name = results[result]["url"].replace("https://", "").replace("http://", "").replace("/", "_").replace("+", "_")
				report_name = re.sub(r"[^a-zA-Z0-9-_. ]", "", report_name)
				
				if report_name.endswith("_"):
					report_name = report_name[:-1]
				
				
				template = original_template
				template = template.replace("{url}", results[result]["url"])
				template = template.replace("{url_resource_id}", result)
				template = template.replace("{date_generated}", str(int(time.time())))
				template = template.replace("{date_generated_pretty}", time.strftime("%B %d, %Y %H:%M:%S"))
				
				fp = open(f"reports/{report_name}.html", 'w')
				fp.write(template)
				fp.close()
			
			
			fp = open("src/script.js", 'r')
			script = fp.read()
			fp.close()
			
			script = script.replace("{json_data}", json.dumps(results, indent=None, separators=(",", ":")))
				
			fp = open("reports/script.js", 'w')
			fp.write(script);
			fp.close()
			
		except Exception as err:
			self.log(f"Error while trying to generate html file: {err}")
	
	
	def parse(self, urls: str, options: dict):
		
		headers = {
			"User-Agent": "Mozilla/5.0 (compatible; ImgOcrValidatorBot/1.0)"
		}
		
		# Print URLs provided
		self.log("URLS = %s" %(urls))
		
		# For each of the URLs provided open 
		for url in urls:
			try:
				m = hashlib.sha1()
				m.update(str(url).encode('utf-8'))
				url_resource_id = m.hexdigest()
				
				self.results[url_resource_id] = {}
				self.results[url_resource_id]["url"] = url
				self.results[url_resource_id]["metrics"] = {}
				self.results[url_resource_id]["resources"] = []
				
				# Fetch HTML
				self.log(f"[{url}] URL Resource Id: {url_resource_id} Fetching source ...")
				start_time = time.process_time()
				response = requests.get(url, headers=headers)
				response.raise_for_status()
				end_time = time.process_time()
				fetch_time = end_time - start_time
				self.results[url_resource_id]["metrics"]["download_time"] = fetch_time
				
				# Parse HTML
				self.log(f"[{url}] Parsing HTML ...")
				start_time = time.process_time()
				soup = BeautifulSoup(response.text, "html.parser")
				end_time = time.process_time()
				parse_time = end_time - start_time
				self.results[url_resource_id]["metrics"]["parse_time"] = parse_time
				
				# Filter out exclusion rules
				if options["exclude"]:
					
					if options["exclude"].startswith("'") and options["exclude"].endswith("'"):
						options["exclude"] = options["exclude"][1:-1]
					if options["exclude"].startswith("\"") and options["exclude"].endswith("\""):
						options["exclude"] = options["exclude"][1:-1]
					
					excluded_selectors = options["exclude"].split(",")
					
					for excluded_selector in excluded_selectors:
						excluded_selector = excluded_selector.strip()
						if not excluded_selector == None and len(excluded_selector) > 0:
							self.log(f"[{url}] Running exclusion rule for '{excluded_selector}' ...")
							for found in soup.select(excluded_selector):
								found.decompose()
				
				# Search HTML for <img> tags
				img_tags = soup.find_all('img')
				img_tags_count = len(img_tags)
				self.log(f"[{url}] Found {img_tags_count} <img> tags (download = {int(round(fetch_time * 1000.0))}ms, parse = {int(round(parse_time * 1000.0))}ms) ...")
				self.results[url_resource_id]["metrics"]["total_images"] = img_tags_count
				
				# For each <img> ... process it
				for img_tag in img_tags:
					
					# Weird case ...
					if not img_tag.has_attr("src"):
						continue
					
					if not img_tag.has_attr("alt"):
						img_tag["alt"] = None
					
					src = img_tag["src"]
					alt = img_tag["alt"]
					
					
					# Generate hash of the SRC url
					m = hashlib.sha1()
					m.update(str(src).encode('utf-8'))
					resource_id = m.hexdigest()
					
					# Ignore duplicate resource id's
					if not options["allow_duplicates"]:
						duplicate = False
						for i in self.results[url_resource_id]["resources"]:
							if i["resource_id"] == resource_id:
								self.log(f"[{url}] - Skipping duplicate resource_id {resource_id} for {src}")
								duplicate = True
								break
						
						if duplicate:
							continue 
					
					index = len(self.results[url_resource_id]["resources"])
					self.results[url_resource_id]["resources"].append({})
					self.results[url_resource_id]["resources"][index]["url"] = src
					self.results[url_resource_id]["resources"][index]["alt"] = alt
					self.results[url_resource_id]["resources"][index]["resource_id"] = resource_id
					self.results[url_resource_id]["resources"][index]["issues"] = []
					
					# If the image is Base64 encoded just ignore it for now
					# TODO: Parse Base64 images for processing
					if src.startswith("data:"):
						self.log(f"[{url}] - Ignoring Base64 encoded image for {img_tag}")
						continue
					
					# Check if url has a protocol
					if not src.startswith("http://") and not src.startswith("https://"):
						if src.startswith("//"):
							purl = urlparse(url)
							src = purl.scheme + ":" + src
						else:
							purl = urlparse(url)
							src = purl.scheme + "://" + purl.netloc + src
					
					# Check if url has trailing whitespace
					if src.endswith(" ") or src.endswith("%20"):
						self.log(f"[{url}] - Url ends with a space {src}")
						self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="warn", text="This image URL ends with a trailing space."))
						src = src.strip()
					
					# Check if the <img src=""> contains a valid URL
					if not self.uri_validator(src):
						self.log(f"[{url}] - Invalid URL for {src}")
						self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="error", text="Invalid URL provided in src attribute."))

					# Check if empty <img alt=""> alt attribute
					if not alt or len(alt.strip()) == 0:
						self.log(f"[{url}] - Empty alt attribute for {src}")
						self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="warn", text="Alt attribute is empty."))

					# Set the URL again after filtering
					self.results[url_resource_id]["resources"][index]["url"] = src

					# Check if the image returns a valid HTTP status code
					self.log(f"[{url}] - Validating source {src} ...")
					try:
						start_time = time.process_time()
						response = requests.get(src, stream=True, timeout=30, headers=headers)
						response.raise_for_status()
						end_time = time.process_time()
						fetch_time = end_time - start_time
						rasterized_image = False
						self.results[url_resource_id]["resources"][index]["download_time"] = fetch_time
						
						# Grab content-type
						if not 'content-type' in response.headers:
							self.log(f"[{url}] - Header 'content-type' is not set for {src}")
							self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="error", text="Header 'content-type' not set. Broken image?"))
							continue
						
						content_type = response.headers['content-type']
						content_type = content_type.lower()
						if ";" in content_type:
							content_type = content_type.split(";")[0]
						self.results[url_resource_id]["resources"][index]["content_type"] = content_type
						
						if content_type == "image/png" or content_type == "image/jpeg" or content_type == "image/gif" or content_type == "image/tiff":
							rasterized_image = True
						
						self.results[url_resource_id]["resources"][index]["rasterized"] = rasterized_image
						
						if not rasterized_image and not content_type == "image/svg" and not content_type == "image/svg+xml":
							self.log(f"[{url}] - Invalid content-type {content_type} for {src}")
							self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="warn", text=f"Invalid headers 'content-type': {content_type}."))
						
						# Ensure content-length is not null
						if not 'content-length' in response.headers:
							self.log(f"[{url}] - Invalid content-length for {src}")
							self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="warn", text=f"Null header 'content-length'."))
						else:
							# Do binary file checks
							if rasterized_image:
								buffer = tempfile.SpooledTemporaryFile(max_size=8e9)
								downloaded = 0
								
								filesize = int(response.headers['content-length'])
								
								for chunk in response.iter_content(chunk_size=1024):
									downloaded += len(chunk)
									buffer.write(chunk)
									#print(downloaded/filesize)
								
								buffer.seek(0)
								img = Image.open(io.BytesIO(buffer.read()))
								buffer.close()
								
								self.results[url_resource_id]["resources"][index]["width"] = img.width
								self.results[url_resource_id]["resources"][index]["height"] = img.height
								
								# Verify width/height if provided in the query params (size/dimensions) ?size=100x100
								if "?" in src:
									size_params = ["size", "dimensions", "dimension", "dim"]
									for size_param in size_params:
										query_param = src.split("?")[1]
										if query_param.startswith(size_param):
											query_value = query_param.split("=")[1]
											if "x" in query_value:
												query_width = query_value.split("x")[0]
												query_height = query_value.split("x")[1]
												if not int(img.width) == int(query_width) or not int(img.height) == int(query_height):
													self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="warn", text=f"Image with query parameters does not match size requested. Expected {query_width}x{query_height} but instead got {img.width}x{img.height}."))
								
								# Analyze using OCR
								img_text_array = pytesseract.image_to_string(img).strip().split()
								
								# Check if the words from the OCR image are real
								d = enchant.Dict("en_US")
								
								cleaned_text = []
								for word in img_text_array:
									if d.check(word):
										cleaned_text.append(word)
										# This word IS real, check if this word exists in the alt attribute
										exists = False
										if not alt == None:
											for w in alt.split(" "):
												if word.lower() in w.lower() or w.lower().startswith(word):
													exists = True

										if not exists:
											self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="info", text=f"Word '{word.lower()}' does not exist in the alt attribute."))

								self.results[url_resource_id]["resources"][index]["analyzed_text"] = ' '.join(cleaned_text)
						
					except HTTPError as http_err:
						self.log(f"[{url}] - HTTP Error: {http_err} for {src}")
						self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="error", text=f"Bad HTTP response, status code: {response.status_code}."))
						continue
					except TimeoutError as timeout_err:
						self.log(f"[{url}] - Timeout Error: {timeout_err} for {src}")
						self.results[url_resource_id]["resources"][index]["issues"].append(dict(severity="error", text=f"Took longer than 30 seconds to get the image."))
						continue

			except KeyboardInterrupt:
				self.log(f"Interrupted!")
			except HTTPError as http_err:
				self.log(f"[{url}] HTTP Error: {http_err} ... skipping this URL")
				continue
			except Exception as err:
				self.log(f"[{url}] An unknown error occured: {err}")
				return
		
		# Save report
		self.log(f"Saving json report ...")
		fp = open("report.json", 'w')
		fp.write(json.dumps(self.results, indent = 4))
		fp.close()

	# Print to console
	def log(self, *msg):
		timestamp = time.strftime("%m-%d-%Y %H:%M:%S")
		msg = " ".join([str(x) for x in msg])
		print(f"{timestamp} {msg}")

	# Validate URL as a string
	def uri_validator(self, url):
		try:
			result = urlparse(url)
			return all([result.scheme, result.netloc])
		except:
			return False


def parse_cli_args():
	parser = argparse.ArgumentParser(prog="img-ocr-validator", description="Launch flags for img-ocr-validator.", exit_on_error=True)
	
	severities = []
	
	for s in Severity:
		severities.append(s.name)
	
	severities_string = ', '.join(map(str, severities))
	
	parser.add_argument("urls", metavar="URL", type=str, nargs="*", help="URLs to analyze.")
	parser.add_argument("-g", "--generate-report", action="store_true", help="Generate HTML reports.")
	parser.add_argument("-p", "--parse-only", action="store_true", help="Generate HTML reports from existing report.json.")
	parser.add_argument("-s", "--severity", type=str, help=f"Only include <SEVERITY> or greater in the report. (Valid severities: {severities_string})")
	parser.add_argument("--exclude", type=str, help="Exclude the presented css selectors. (Separated by , (commas))")
	parser.add_argument("--allow-duplicates", action="store_true", help="Ignore duplicate resource id's (may cause unexpected results!)")
	
	args = parser.parse_args()
	
	generate_report = args.generate_report or False
	parse_only = args.parse_only or False
	severity = args.severity or False
	exclude = args.exclude or False
	allow_duplicates = args.allow_duplicates or False
	
	if not severity == False and (not severity == "NONE" and not severity == "INFO" and not severity == "WARN" and not severity == "ERROR"):
		print(f"Error: Severity must be {severities_string}")
		return 100
	
	for s in Severity:
		if s.name == severity:
			severity = s
	
	options = {}
	options["generate_report"] = generate_report
	options["parse_only"] = parse_only
	options["severity"] = severity
	options["exclude"] = exclude
	options["allow_duplicates"] = allow_duplicates
	
	ImgOCRValidator(args.urls, options)

if __name__ == '__main__':
	parse_cli_args()


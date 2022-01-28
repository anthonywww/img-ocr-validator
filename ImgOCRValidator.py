import os
import io
import re
import sys
import json
import time
import requests
import requests.exceptions
import enchant
import tempfile
import pytesseract
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from PIL import Image

class ImgOCRValidator():

	def __init__(self, urls: str, generate_html_report: bool, only_generate_report: bool, use_legacy_html_report: bool):
		
		# Check if only generating HTML report from existing report.json
		if only_generate_report:
			try:
				fp = open("report.json", 'r')
				json_report = json.loads(fp.read())
				fp.close()
				if use_legacy_html_report:
					self.generate_legacy_report(json_report)
				else:
					self.generate_report(json_report)
			except Exception as err:
				self.log(f"Error while trying to read report.json file: {err}")
			return
		
		# Check if URLs are valid
		for url in urls:
			if not self.uri_validator(url):
				raise Exception(f"Invalid URL provided: {url}")
		
		if len(urls) == 0:
			raise Exception("No URLs provided")
		
		self.results = {}
		self.parse(urls)
		
		if generate_html_report:
			if use_legacy_html_report:
				self.generate_legacy_report(self.results)
			else:
				self.generate_report(self.results)

	def generate_report(self, results):
		self.log(f"Saving html report ...")
		
		try:
			fp = open("src/template.html", 'r')
			template = fp.read()
			template = template.replace("{json_data}", json.dumps(results, indent=None, separators=(",", ":")))
			template = template.replace("{date_generated}", time.strftime("%m-%d-%Y %H:%M:%S"))
			fp.close()
			
			fp = open("report.html", 'w')
			fp.write(template)
			fp.close()
		except Exception as err:
			self.log(f"Error while trying to read template html file: {err}")
		

	def generate_legacy_report(self, results):
		import json2html
		
		self.log(f"Saving legacy html report ...")
		
		try:
			fp = open("src/_header.html", 'r')
			header = fp.read()
			header = header.replace("{date_generated}", time.strftime("%m-%d-%Y %H:%M:%S"))
			fp.close()
			
			fp = open("src/_footer.html", 'r')
			footer = fp.read()
			footer = footer.replace("{date_generated}", time.strftime("%m-%d-%Y %H:%M:%S"))
			fp.close()
			
			# Create reports/ directory
			if not os.path.isdir("reports"):
				os.mkdir("reports")
			
			for result in results:
				report = json2html.json2html.convert(json=results[result]["images"])
				
				if report.endswith("/"):
					report = report[:-1]
				
				report_name = result.replace("https://", "").replace("http://", "").replace("/", "_")
				report_name = re.sub(r"[^a-zA-Z0-9-_. ]", "", report_name)
				
				fp = open(f"reports/{report_name}.html", 'w')
				fp.write(header)
				fp.write(report)
				fp.write(footer)
				fp.close()
				
				
		except Exception as err:
			self.log(f"Error while trying to read legacy template html files: {err}")


	def parse(self, urls: str):
		# Print URLs provided
		self.log("URLS = %s" %(urls))
		
		# For each of the URLs provided open 
		for url in urls:
			try:
				self.results[url] = {}
				self.results[url]["metrics"] = {}
				self.results[url]["images"] = []
				
				# Fetch HTML
				self.log(f"[{url}] Fetching source ...")
				start_time = time.process_time()
				response = requests.get(url)
				response.raise_for_status()
				end_time = time.process_time()
				fetch_time = end_time - start_time
				self.results[url]["metrics"]["download_time"] = fetch_time
				
				# Parse HTML
				self.log(f"[{url}] Parsing HTML ...")
				start_time = time.process_time()
				soup = BeautifulSoup(response.text, "html.parser")
				end_time = time.process_time()
				parse_time = end_time - start_time
				self.results[url]["metrics"]["parse_time"] = parse_time
				
				# Search HTML for <img> tags
				img_tags = soup.find_all('img')
				img_tags_count = len(img_tags)
				self.log(f"[{url}] Found {img_tags_count} <img> tags (download = {int(round(fetch_time * 1000.0))}ms, parse = {int(round(parse_time * 1000.0))}ms) ...")
				self.results[url]["metrics"]["total_images"] = img_tags_count
				
				# For each <img> ... process it
				for img_tag in img_tags:
					
					# Weird case ...
					if not img_tag.has_attr("src"):
						continue
					
					if not img_tag.has_attr("alt"):
						img_tag["alt"] = None
					
					path = self.get_css_path(img_tag)
					src = img_tag["src"]
					alt = img_tag["alt"]
					
					index = len(self.results[url]["images"])
					self.results[url]["images"].append({})
					self.results[url]["images"][index]["url"] = src
					self.results[url]["images"][index]["alt"] = alt
					self.results[url]["images"][index]["path"] = path
					self.results[url]["images"][index]["issues"] = []
					
					# If the image is Base64 encoded just ignore it for now
					# TODO: Parse Base64 images for processing
					if src.startswith("data:"):
						self.log(f"[{url}] - Ignoring Base64 encoded image for {img_tag}")
						continue
					
					# Check if url has a protocol
					if not src.startswith("http://") and not src.startswith("https://"):
						purl = urlparse(url)
						src = purl.scheme + "://" + purl.netloc + src
					
					# Check if the <img src=""> contains a valid URL
					if not self.uri_validator(src):
						self.log(f"[{url}] - Invalid URL for {src}")
						self.results[url]["images"][index]["issues"].append(dict(severity="error", text="Invalid URL provided in src attribute."))

					# Check if empty <img alt=""> alt attribute
					if not alt or len(alt.strip()) == 0:
						self.log(f"[{url}] - Empty alt attribute for {src}")
						self.results[url]["images"][index]["issues"].append(dict(severity="warn", text="Alt attribute is empty."))

					# Check if the image returns a valid HTTP status code
					self.log(f"[{url}] - Validating source {src} ...")
					try:
						start_time = time.process_time()
						response = requests.get(src, stream=True, timeout=30)
						response.raise_for_status()
						end_time = time.process_time()
						fetch_time = end_time - start_time
						rasterized_image = False
						self.results[url]["images"][index]["download_time"] = fetch_time
						
						# Grab content-type
						content_type = response.headers['content-type']
						content_type = content_type.lower()
						if ";" in content_type:
							content_type = content_type.split(";")[0]
						self.results[url]["images"][index]["content_type"] = content_type
						
						if content_type == "image/png" or content_type == "image/jpeg" or content_type == "image/gif" or content_type == "image/tiff":
							rasterized_image = True
						
						self.results[url]["images"][index]["rasterized"] = rasterized_image
						
						if not rasterized_image and not content_type == "image/svg" and not content_type == "image/svg+xml":
							self.log(f"[{url}] - Invalid content-type {content_type} for {src}")
							self.results[url]["images"][index]["issues"].append(dict(severity="warn", text=f"Invalid headers 'content-type': {content_type}."))
						
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
							
							self.results[url]["images"][index]["width"] = img.width
							self.results[url]["images"][index]["height"] = img.height
							
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
												self.results[url]["images"][index]["issues"].append(dict(severity="warn", text=f"Image with query parameters does not match size requested. Expected {query_width}x{query_height} but instead got {img.width}x{img.height}."))
							
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
									for w in alt.split(" "):
										if word.lower() in w.lower() or w.lower().startswith(word):
											exists = True

									if not exists:
										self.results[url]["images"][index]["issues"].append(dict(severity="info", text=f"Word '{word.lower()}' does not exist in the alt attribute."))

							self.results[url]["images"][index]["analyzed_text"] = ' '.join(cleaned_text)
						
					except HTTPError as http_err:
						self.log(f"[{url}] - HTTP Error: {http_err} for {src}")
						self.results[url]["images"][index]["issues"].append(dict(severity="error", text=f"Bad HTTP response, status code: {response.status_code}."))
						continue
					except TimeoutError as timeout_err:
						self.log(f"[{url}] - Timeout Error: {timeout_err} for {src}")
						self.results[url]["images"][index]["issues"].append(dict(severity="error", text=f"Took longer than 30 seconds to get the image."))
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
		

	# https://stackoverflow.com/questions/25969474/beautifulsoup-extract-xpath-or-css-path-of-node
	def get_element(self, node):
		# for XPATH we have to count only for nodes with same type!
		length = len(list(node.previous_siblings)) + 1
		if (length) > 1:
			return '%s:nth-child(%s)' % (node.name, length)
		else:
			return node.name

	# https://stackoverflow.com/questions/25969474/beautifulsoup-extract-xpath-or-css-path-of-node
	def get_css_path(self, node):
		path = [self.get_element(node)]
		for parent in node.parents:
			if parent.name == 'body':
				break
			path.insert(0, self.get_element(parent))
		return ' > '.join(path)

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


def parse_cli_args(args):
	binary = args.pop(0)
	
	generate_html_report = False
	only_generate_report = False
	use_legacy_html_report = False
	urls = []
	
	for arg in args:
		if not arg.startswith("-"):
			urls.append(arg)
		else:
			if arg == "-h" or arg == "--help" or arg == "-?":
				print(f"Usage: {binary} [args] <URLS>")
				print(f" -h, -?, --help ....... Show all args.")
				print(f" -g ................... Generate HTML report.")
				print(f" -p ................... Generate HTML report from existing report.json.")
				print(f" -k ................... Use the legacy HTML reporter.")
				return
			if arg == "-g":
				generate_html_report = True
			if arg == "-p":
				only_generate_report = True
			if arg == "-k":
				use_legacy_html_report = True
			
	ImgOCRValidator(urls, generate_html_report, only_generate_report, use_legacy_html_report)

if __name__ == '__main__':
	parse_cli_args(sys.argv)



// Default value for dark-mode
var dark_mode = false;
const full_report = {json_data};
var json_report = full_report;

String.prototype.hashCode = function() {
	var hash = 0;
	for (var i = 0; i < this.length; i++) {
		var char = this.charCodeAt(i);
		hash = ((hash<<5)-hash)+char;
		hash = hash & hash; // Convert to 32-bit integer
	}
	return hash;
}

const severities = {
	"none": {"value": 0, "style": ""},
	"info": {"value": 1, "style": "is-info"},
	"warn": {"value": 2, "style": "is-warning"},
	"error": {"value": 3, "style": "is-danger"}
}

function renderReport(data) {

	$container = $("#report_breakdown_data");
	$container.html("");

	for (var i in data) {
	
		// Mandatory
		var object = data[i];
		var url = object["url"];
		var alt = object["alt"];
		var issues = object["issues"];
		var download_time = object["download_time"];
		var content_type = object["content_type"];
		var rasterized = object["rasterized"];
		
		var rid = Math.abs(url.hashCode()).toString(16);
		
		// Optional
		var width = object["width"];
		var height = object["height"];
		var analyzed_text = object["analyzed_text"];
		
		var max_severity = 0;
		for (var i in issues) {
			for (var s in severities) {
				var sev = issues[i].severity;
				if (sev && sev == s) {
					max_severity = Math.max(severities[sev].value, max_severity);
					break;
				}
			}
		}
		
		var max_severity_name = "NONE";
		
		for (s in severities) {
			if (severities[s].value == max_severity) {
				max_severity_name = s;
				break;
			}
		}
		
		var severity_style = "";
		
		if (max_severity > 0) {
			for (var s in severities) {
				if (severities[s].value == max_severity) {
					severity_style = severities[s].style;
				}
			}
		}
		
		var $root = $(`<article id="resource_${rid}">`);
		$root.addClass("message");
		$root.addClass(severity_style);
		
		var $message_header = $("<div>");
		$message_header.addClass("message-header");
		
		$message_header.append(`
			<p><a href="#resource_${rid}"><i class="fa fa-hashtag"></i></a> Resource: ${rid}</p>
			<button class="delete"></button>
			<!--
			<label class="checkbox" for="checked_${rid}">
				<input type="checkbox" id="checked_${rid}" name="checked_${rid}">
				Reviewed?
			</label>
			-->
		`);
		
		var $message_body = $("<div>");
		$message_body.addClass("message-body");
		$message_body.addClass("content");
		
		
		var issues_table = "";
		
		if (issues.length > 0) {
			issues_table = $("<table>");
			
			for (var i in issues) {
				var severity = issues[i].severity;
				var text = issues[i].text;
				/*
				issues_table.append(`
					<tr>
						<th>Severity</th>
						<td class="severity severity-${severity}">${severity.toUpperCase()}</td>
					</tr>
					<tr>
						<th>Message</th>
						<td>${text}</td>
					</tr>
				`);
				*/
				issues_table.append(`
					<p><span class='severity severity-${severity}'>${severity.toUpperCase()}</span>&nbsp;${text}</p>
				`);
			}
			
			//issues_table = "<table>" + issues_table.html() + "</table>";
			issues_table = "<div class='content'>" + issues_table.html() + "</div>";
		}
		
		
		
		
		let rasterized_info = "";
		if (rasterized) {
			rasterized_info = `
				<table>
					<tr>
						<th>Width</th>
						<td>${width}</td>
					</tr>
					<tr>
						<th>Height</th>
						<td>${height}</td>
					</tr>
					<tr>
						<th>Analyzed Text</th>
						<td>${analyzed_text}</td>
					</tr>
				</table>
			`;
		}
		
		
		let body = `
			<div class="columns">
				<div class="column is-10">
					<table>
						<tr>
							<th>URL</th>
							<td><a target="_blank" href="${url}">${url}</a></td>
						</tr>
						<tr>
							<th>ALT Text</th>
							<td>${alt}</td>
						</tr>
						<tr>
							<th>Issues</th>
							<td>${issues_table}</td>
						</tr>
						<tr>
							<th>Content Type</th>
							<td>${content_type}</td>
						</tr>
						<tr>
							<th>Rasterized Information</th>
							<td>${rasterized_info}</td>
						</tr>
						<tr>
							<th>Download Time</th>
							<td>${download_time}</td>
						</tr>
					</table>
				</div>
				<div class="column is-2">
					<a target="_blank" href="${url}"><img class="preview-image" src="${url}"></a>
				</div>
			</div>
		`;
		
		$message_body.append(body);
		
		$root.append($message_header);
		$root.append($message_body);
		
		$container.append($root);
	}
	
	// On remove button click
	$("button.delete").click(function() {
		$(this).parent().parent().remove();
	});
	
}

// On DOM load
document.addEventListener("DOMContentLoaded", function() {

	// Dark mode options
	$("#dark_mode").click(function() {
		dark_mode = !dark_mode;
		if (dark_mode) {
			$("html").addClass("dark-mode");
			$("body").addClass("dark-mode");
			$("h1,h2,h3,h4,h5,h6").addClass("dark-mode");
			$(".footer").addClass("dark-mode");
			
			$("#dark_mode").children().addClass("fa-sun");
			$("#dark_mode").children().removeClass("fa-moon");
		} else {
			$("html").removeClass("dark-mode");
			$("body").removeClass("dark-mode");
			$("h1,h2,h3,h4,h5,h6").removeClass("dark-mode");
			$(".footer").removeClass("dark-mode");
			
			$("#dark_mode").children().addClass("fa-moon");
			$("#dark_mode").children().removeClass("fa-sun");
		}
	});
	
	// Set JSON report
	$("#raw_json_data button").click(function () {
		$(this).parent().html(`
			<pre><code style="border-radius:8px;" class="language-json">${JSON.stringify(full_report, null, 4)}</code></pre>
		`);
		hljs.highlightAll();
	});
	
	renderReport(json_report);
	
});

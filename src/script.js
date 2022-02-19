const full_report = {json_data};
const severities = {
	"none": {"value": 0, "style": "is-success"},
	"info": {"value": 1, "style": "is-info"},
	"warn": {"value": 2, "style": "is-warning"},
	"error": {"value": 3, "style": "is-danger"}
};
const default_filter = {
	"severity": {
		"none": true,
		"info": true,
		"warn": true,
		"error": true
	},
	"resource_type": "any",
	"search": {
		"alt": ""
	},
	"excluded": []
};

let dark_mode = false;
let json_report = null;
// Hack to deep-copy the filters, not reference
let filter = JSON.parse(JSON.stringify(default_filter));


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
		var rid = object["resource_id"];
		
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
		
		for (var s in severities) {
			if (severities[s].value == max_severity) {
				max_severity_name = s;
				break;
			}
		}
		
		var severity_style = "is-success";
		
		if (max_severity > 0) {
			for (var s in severities) {
				if (severities[s].value == max_severity) {
					severity_style = severities[s].style;
				}
			}
		}
		
		var $root = $(`<article id="resource_${rid}" data-resource-id="${rid}">`);
		$root.addClass("message");
		$root.addClass(severity_style);
		
		var $message_header = $("<div>");
		$message_header.addClass("message-header");
		
		$message_header.append(`
			<p><a href="#resource_${rid}"><i class="fa fa-hashtag"></i></a> Resource Id: ${rid}</p>
			<button class="delete"></button>
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
				issues_table.append(`
					<p><span class='tag ${severities[severity].style}'>${severity.toUpperCase()}</span>&nbsp;${text}</p>
				`);
			}
			
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
	// This must be done AFTER the rendering is complete, otherwise the .click() bind is unbound.
	$("#report_breakdown_data button.delete").click(function() {
		var resource_id = $(this).parent().parent().attr("data-resource-id");
		
		if (!(resource_id in filter["excluded"])) {
			filter["excluded"].push(resource_id);
		}
		
		$(this).parent().parent().remove();
	});
	
}


function process(resource, r) {
	
	// Check if resource was manually removed
	for (let i in filter["excluded"]) {
		if (resource["resource_id"] == filter["excluded"][i]) {
			return false;
		}
	}
	
	// Severity filters
	if (resource.issues.length > 0) {
		// Go through each issue ...
		for (var i in resource.issues) {
			let severity = resource.issues[i].severity;
			
			for (var j in filter.severity) {
				if (j == "none") {continue;}
				
				if (severity == j && !filter.severity[j]) {
					return false;
				}
			}
			
		}
	} else {
		if (!filter.severity.none) {
			return false;
		}
	}
	
	// Resource Type
	if (filter["resource_type"] == "rasterized") {
		if (!resource.rasterized || resource.content_type == undefined) {
			return false;
		}
	} else if(filter["resource_type"] == "not_rasterized") {
		if(resource.rasterized || resource.content_type == undefined) {
			return false;
		}
	}
	
	// Alt text search
	let alt_search_string = filter.search.alt.trim();
	if (alt_search_string.length > 0) {
		if (resource.alt) {
			if (!resource.alt.toString().toLowerCase().includes(alt_search_string.toLowerCase())) {
				return false;
			}
		} else {
			return false;
		}
	}
	
	
	
	return true;
}


function runReportFilter() {

	if (filter.resetting) {
		return;
	}
	
	var results = [];
	
	for (let r in json_report) {
		let resource = json_report[r];
		let include = process(resource, r);
		if (include) {
			results.push(resource);
		}
	}
	
	renderReport(results);
}

function timeDifference(current, previous) {
	var msPerMinute = 60 * 1000;
	var msPerHour = msPerMinute * 60;
	var msPerDay = msPerHour * 24;
	var msPerMonth = msPerDay * 30;
	var msPerYear = msPerDay * 365;

	var elapsed = current - previous;

	if (elapsed < msPerMinute) {
		return Math.round(elapsed/1000) + ' seconds ago';
	} else if (elapsed < msPerHour) {
		return Math.round(elapsed/msPerMinute) + ' minutes ago';
	} else if (elapsed < msPerDay ) {
		return Math.round(elapsed/msPerHour ) + ' hours ago';
	} else if (elapsed < msPerMonth) {
		return 'approximately ' + Math.round(elapsed/msPerDay) + ' days ago';
	} else if (elapsed < msPerYear) {
		return 'approximately ' + Math.round(elapsed/msPerMonth) + ' months ago';
	} else {
		return 'approximately ' + Math.round(elapsed/msPerYear ) + ' years ago';
	}
}

function updateTimestamps() {
	$("time.timestamp").each(function() {
		let previous_string = parseInt(($(this).attr("datetime")));
		
		let previous = new Date(previous_string * 1000);
		let current = new Date();
		let diff = timeDifference(current, previous);
		
		$(this).attr("title", diff);
	});
}



// On DOM load
document.addEventListener("DOMContentLoaded", function() {

	// Set relevant report
	json_report = full_report[$("#url_resource_id").val()]["resources"];
	
	// Set relative time hover, updated every second
	setInterval(updateTimestamps, 1000);
	updateTimestamps();

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
	
	
	
	
	// ---------------
	// Set JSON report
	// ---------------
	let json_hidden = true;
	$("#raw_json_data button").click(function() {
		if (json_hidden) {
			$(this).text("Hide JSON");
			$(this).parent().append(`
				<pre><code style="border-radius:8px;" class="language-json">${JSON.stringify(json_report, null, 4)}</code></pre>
			`);
			hljs.highlightAll();
		} else {
			$(this).text("Show JSON");
			$("#raw_json_data pre").remove();
		}
		
		json_hidden = !json_hidden;
	});
	
	let total_issues_none = 0;
	let total_issues_info = 0;
	let total_issues_warn = 0;
	let total_issues_error = 0;
	
	for (let i in json_report) {
		let resource = json_report[i];
		if (resource.issues.length == 0) {
			total_issues_none++;
		} else {
			for (let j in resource.issues) {
				let issue = resource.issues[j];
				if (issue.severity == "info") {
					total_issues_info++;
				} else if (issue.severity == "warn") {
					total_issues_warn++;
				} else if (issue.severity == "error") {
					total_issues_error++;
				}
			}
		}
	}
	
	$("#filter_severity_none").next("span.tag").text(`NONE (${total_issues_none})`);
	$("#filter_severity_info").next("span.tag").text(`INFO (${total_issues_info})`);
	$("#filter_severity_warn").next("span.tag").text(`WARN (${total_issues_warn})`);
	$("#filter_severity_error").next("span.tag").text(`ERROR (${total_issues_error})`);
	
	
	// -------
	// Filters
	// -------	
	$("#filter_run").click(function() {
		runReportFilter();
	});
	$("#filter_reset").click(function() {
	
		filter.resetting = true;
		
		// Reset options
		$("#filter_severity_none").prop("checked", true);
		$("#filter_severity_info").prop("checked", true);
		$("#filter_severity_warn").prop("checked", true);
		$("#filter_severity_error").prop("checked", true);
		$("#filter_resource_type").val("any").change();
		$("#filter_search_alt").val("");
		
		// Reset to filter and report to default values
		// Hack to deep-copy default filters, not reference
		filter = JSON.parse(JSON.stringify(default_filter));
		json_report = full_report[$("#url_resource_id").val()]["resources"];
		
		runReportFilter();
	});
	$("#filter_severity_none").change(function() {
		filter["severity"]["none"] = !filter["severity"]["none"];
		runReportFilter();
	});
	$("#filter_severity_info").change(function() {
		filter["severity"]["info"] = !filter["severity"]["info"];
		runReportFilter();
	});
	$("#filter_severity_warn").change(function() {
		filter["severity"]["warn"] = !filter["severity"]["warn"];
		runReportFilter();
	});
	$("#filter_severity_error").change(function() {
		filter["severity"]["error"] = !filter["severity"]["error"];
		runReportFilter();
	});
	$("#filter_resource_type").change(function() {
		filter["resource_type"] = $(this).children("option:selected").val();
		runReportFilter();
	});
	$("#filter_search_alt").on('input', function() {
		filter["search"]["alt"] = $(this).val();
		runReportFilter();
	});
	
	
	runReportFilter();
});

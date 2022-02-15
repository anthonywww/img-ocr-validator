
// Default value for dark-mode
var dark_mode = false;

// On DOM load
document.addEventListener("DOMContentLoaded", function() {

	// Highlight JS
	hljs.highlightAll();

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
	
	// Populate Report Breakdown
	$("#report_breakdown_data").text("test");
	
	$("#raw_json_data pre code").text(raw_json_data);
	
	
});

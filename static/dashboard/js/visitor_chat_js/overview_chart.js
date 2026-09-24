// ApexCharts overview chart — defers render until tab is visible
var overviewChart = null;
var overviewRendered = false;

function renderOrUpdateChart(data) {
    var el = document.querySelector("#line_area_charts");
    if (!el) return;

    if (overviewRendered && overviewChart) {
        // Already rendered — just update
        overviewChart.updateOptions({
            xaxis: { categories: data.categories }
        });
        overviewChart.updateSeries([
            { name: "Conversations", type: "bar", data: data.conversations },
            { name: "Messages", type: "bar", data: data.messages },
            { name: "Visitors", type: "area", data: data.visitors }
        ]);
        console.log("Chart updated with data");
    } else {
        // First render — build options with data
        var opts = {
            series: [
                { name: "Conversations", type: "bar", data: data.conversations },
                { name: "Messages", type: "bar", data: data.messages },
                { name: "Visitors", type: "area", data: data.visitors }
            ],
            chart: {
                height: 430,
                type: "line",
                stacked: false,
                toolbar: { show: false }
            },
            colors: ["#5969aa", "#2ec4b6", "#3498db"],
            stroke: { width: [0, 0, 4], curve: "smooth" },
            plotOptions: {
                bar: { horizontal: false, columnWidth: "35%", borderRadius: 5 }
            },
            fill: {
                opacity: [1, 1, 0.45],
                gradient: {
                    shade: "light", type: "vertical",
                    opacityFrom: 0.7, opacityTo: 0.15, stops: [0, 100]
                }
            },
            dataLabels: { enabled: false },
            markers: { size: 0 },
            xaxis: {
                categories: data.categories,
                axisBorder: { show: false }
            },
            yaxis: {
                min: 0,
                forceNiceScale: true,
                labels: { formatter: function(val) { return parseInt(val); } }
            },
            grid: { borderColor: "#e9ecef", strokeDashArray: 3 },
            legend: { position: "bottom", horizontalAlign: "left", markers: { radius: 12 } },
            tooltip: { shared: true, intersect: false }
        };

        overviewChart = new ApexCharts(el, opts);
        overviewChart.render()
            .then(function() {
                overviewRendered = true;
                console.log("Chart rendered with data");
            })
            .catch(function(e) {
                console.error("Render error:", e);
            });
    }
}

function loadOverviewChart(chartType, branch) {
    chartType = chartType || "daily";
    branch = branch || "";
    var period = typeof gPeriod !== 'undefined' ? gPeriod : "today";

    var url = "/dashboard/visitor_chat/api/charts/?chart=" + encodeURIComponent(chartType) +
              "&period=" + encodeURIComponent(period) +
              "&branch=" + encodeURIComponent(branch);
    
    if (period === 'custom') {
        const from = document.getElementById('customFrom')?.value;
        const to = document.getElementById('customTo')?.value;
        if (from) url += "&from_date=" + encodeURIComponent(from);
        if (to) url += "&to_date=" + encodeURIComponent(to);
    }
    
    console.log("Fetching chart data from:", url);
    
    return fetch(url)
        .then(function(response) {
            if (!response.ok) throw new Error("HTTP " + response.status);
            return response.json();
        })
        .then(function(data) {
            if (!data || !data.overview) {
                console.error("Missing overview in response:", data);
                return;
            }
            console.log("Categories:", JSON.stringify(data.overview.categories));
            console.log("Conversations:", JSON.stringify(data.overview.conversations));
            console.log("Messages:", JSON.stringify(data.overview.messages));
            console.log("Visitors:", JSON.stringify(data.overview.visitors));
            renderOrUpdateChart(data.overview);
        })
        .catch(function(error) {
            console.error("Overview chart error:", error);
        });
}

    
  
  
  
 
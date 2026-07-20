// -----------------------------
// Dynamic Data from Django
// -----------------------------
const labelsEl = document.getElementById("pie-labels");
const valuesEl = document.getElementById("pie-values");

if (!labelsEl || !valuesEl) {
    console.error("pie_chart.js: Missing #pie-labels or #pie-values json_script elements");
} 

const pieLabels = labelsEl ? JSON.parse(labelsEl.textContent) : [];
const pieSeries = valuesEl ? JSON.parse(valuesEl.textContent) : [];

if (!Array.isArray(pieLabels) || !Array.isArray(pieSeries)) {
    console.error("pie_chart.js: pie-labels and pie-values must be JSON arrays", {
        pieLabelsType: typeof pieLabels,
        pieSeriesType: typeof pieSeries,
        pieLabels,
        pieSeries,
    });
}

console.log("Pie Labels:", pieLabels);
console.log("Pie Values:", pieSeries);

// -----------------------------
// Donut Chart
// -----------------------------
var options = {
    series: pieSeries,
    chart: {
        type: "donut",
        height: 0,
        toolbar: {
            show: false
        }
    },
    labels: pieLabels,


    colors: [
        "#6C63FF", // Monday
        "#FF6384", // Tuesday
        "#FFC75F", // Wednesday
        "#00C9A7", // Thursday
        "#4D96FF", // Friday
        "#B983FF", // Saturday
        "#4CAF50"  // Sunday
    ],

    plotOptions: {
        pie: {

            expandOnClick: true,

            donut: {

                size: "68%",

                labels: {

                    show: true,

                    name: {
                        show: true
                    },

                    value: {
                        show: true,

                        formatter: function (val) {
                            return "₹" + Number(val).toLocaleString("en-IN");
                        }
                    },

                    total: {

                        show: true,

                        label: "Total",

                        formatter: function (w) {

                            let total = w.globals.seriesTotals.reduce(function (a, b) {
                                return a + b;
                            }, 0);

                            return "₹" + Number(total).toLocaleString("en-IN");
                        }
                    }
                }
            }
        }
    },

    dataLabels: {

        enabled: true,

        formatter: function (val, opts) {

            const amount = opts.w.globals.series[opts.seriesIndex];

            if (amount <= 0) {
                return "";
            }

            return "₹" + Number(amount).toLocaleString("en-IN");
        },

        style: {
            fontSize: "12px",
            fontWeight: "bold",
            colors: ["#ffffff"]
        },

        dropShadow: {
            enabled: false
        }
    },

    stroke: {
        width: 3,
        colors: ["#fff"]
    },

    legend: {

        show: true,

        position: "right",

        fontSize: "14px",

        formatter: function (seriesName, opts) {

            const amount = opts.w.globals.series[opts.seriesIndex];

            return seriesName + " - ₹" + Number(amount).toLocaleString("en-IN");
        }
    },

    tooltip: {

        y: {

            formatter: function (val) {

                return "₹" + Number(val).toLocaleString("en-IN");
            }
        }
    },

    responsive: [
        {
            breakpoint: 768,
            options: {
                chart: {
                    height: 350
                },
                legend: {
                    position: "bottom"
                }
            }
        }
    ]
};

// -----------------------------
// Render
// -----------------------------
document.querySelector("#pie-color").innerHTML = "";

var chart = new ApexCharts(
    document.querySelector("#pie-color"),
    options
);

chart.render();
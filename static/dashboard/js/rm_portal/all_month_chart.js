

const branchCategories = JSON.parse(
    document.getElementById("branch-categories").textContent
);

const branchValues = JSON.parse(
    document.getElementById("branch-values").textContent
);

console.log("Branch Categories:", branchCategories);
console.log("Branch Values:", branchValues);

// ===============================
// Dynamic Y Axis
// ===============================

const branchMaxValue = Math.max(...branchValues, 0);

const labelCount = 5;

let step = Math.ceil(branchMaxValue / (labelCount - 1));

if (step <= 1000) {
    step = Math.ceil(step / 100) * 100;
} else if (step <= 10000) {
    step = Math.ceil(step / 1000) * 1000;
} else if (step <= 100000) {
    step = Math.ceil(step / 10000) * 10000;
} else if (step <= 1000000) {
    step = Math.ceil(step / 50000) * 50000;
} else {
    step = Math.ceil(step / 100000) * 100000;
}

const branchYAxisMax =
    branchMaxValue === 0
        ? 100
        : step * (labelCount - 1);

// ===============================
// Chart Options
// ===============================

const branchChartOptions = {

    series: [{
        name: "This Month Revenue",
        data: branchValues
    }],

    chart: {
        type: "bar",
        height: 420,
        toolbar: {
            show: false
        },
        background: "transparent",
        dropShadow: {
            enabled: true,
            top: 8,
            left: 0,
            blur: 10,
            opacity: 0.15
        }
    },

    colors: [
        "#06B6D4",
        "#e83ab4",
        "#F97316"
    ],

    plotOptions: {
        bar: {
            horizontal: false,
            distributed: true,
            columnWidth: "45%",
            borderRadius: 15,
            borderRadiusApplication: "end",
            borderRadiusWhenStacked: "last",

            dataLabels: {
                position: "top"
            }
        }
    },

    dataLabels: {
        enabled: true,
        offsetY: -20,

        style: {
            fontSize: "14px",
            fontWeight: "700",
            colors: ["#374151"]
        },

        formatter: function (val) {
            return "₹ " + Number(val).toLocaleString("en-IN");
        }
    },

    xaxis: {
        categories: branchCategories,

        labels: {
            style: {
                fontSize: "14px",
                fontWeight: 600
            }
        },

        axisBorder: {
            show: false
        },

        axisTicks: {
            show: false
        }
    },

    yaxis: {
        min: 0,
        max: branchYAxisMax,
        tickAmount: labelCount - 1,
        forceNiceScale: true,

        labels: {
            formatter: function (val) {
                return "₹ " + Number(val).toLocaleString("en-IN");
            }
        }
    },

    grid: {
        borderColor: "#E5E7EB",
        strokeDashArray: 5,

        padding: {
            left: 20,
            right: 20
        }
    },

    legend: {
        show: false
    },

    title: {
        text: "Branch Revenue - This Month",
        align: "left",

        style: {
            fontSize: "20px",
            fontWeight: "700"
        }
    },

    subtitle: {
        text: "Monthly Revenue Performance",

        style: {
            fontSize: "13px",
            color: "#6B7280"
        }
    },

    tooltip: {
        theme: "light",

        y: {
            formatter: function (val) {
                return "₹ " + Number(val).toLocaleString("en-IN");
            }
        }
    }

};

// ===============================
// Render Chart
// ===============================

const branchRevenueChart = new ApexCharts(
    document.querySelector("#rmPortalBranchChart"),
    branchChartOptions
);

branchRevenueChart.render();
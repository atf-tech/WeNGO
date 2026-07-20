// Today's 24 Hours Donation Collection Chart

const categories = JSON.parse(
    document.getElementById("gradient-categories").textContent
);

const values = JSON.parse(
    document.getElementById("gradient-values").textContent
);

// Dynamic Y-Axis
const maxValue = Math.max(...values);
const yAxisMax = maxValue === 0 ? 100 : Math.ceil(maxValue * 1.2);

var options = {
    series: [
        {
            name: "Donation Amount",
            data: values
        }
    ],

    chart: {
        height: 350,
        type: "line",
        toolbar: {
            show: false
        }
    },

    stroke: {
        width: 5,
        curve: "smooth"
    },

    xaxis: {
        categories: categories,
        tickAmount: 24,

        title: {
            text: "Hours"
        },

        labels: {
            rotate: -45,
            hideOverlappingLabels: true,
            style: {
                fontSize: "11px"
            }
        }
    },

    yaxis: {
        min: 0,
        max: yAxisMax,
        tickAmount: 5,

        title: {
            text: "Donation Amount (₹)"
        },

        labels: {
            formatter: function (value) {
                return "₹" + Math.round(value).toLocaleString();
            }
        }
    },

    dataLabels: {
        enabled: true,

        formatter: function (val) {
            return "₹" + val.toLocaleString();
        },

        offsetY: -10,

        style: {
            fontSize: "10px"
        },

        background: {
            enabled: false
        }
    },

    markers: {
        size: 6,

        hover: {
            size: 8
        }
    },

    tooltip: {
        y: {
            formatter: function (value) {
                return "₹" + value.toLocaleString();
            }
        }
    },

    title: {
        text: "Today's 24 Hours Donation Collection",
        align: "left",

        style: {
            fontSize: "16px",
            color: "#666"
        }
    },

    fill: {
        type: "gradient",

        gradient: {
            shade: "dark",
            gradientToColors: ["#f335fd"],
            shadeIntensity: 1,
            type: "horizontal",
            opacityFrom: 1,
            opacityTo: 1,
            stops: [0, 100]
        }
    },

    colors: ["#405189"],

    grid: {
        borderColor: "#f1f1f1",
        strokeDashArray: 4
    }
};

var chart = new ApexCharts(
    document.querySelector("#gradient-chat"),
    options
);

chart.render();
const monthCategories = JSON.parse(
    document.getElementById("month-categories").textContent
);

const monthValues = JSON.parse(
    document.getElementById("month-values").textContent
);

var options = {

    series: [{
        name: "Income",
        data: monthValues
    }],

    chart: {
        height: 350,
        type: "bar",
        toolbar: {
            show: false
        }
    },

    plotOptions: {
        bar: {
            borderRadius: 12,
            columnWidth: "50%",
            distributed: true,
            dataLabels: {
                position: "top"
            }
        }
    },

    colors: [
        "#6C63FF",
        "#FF6B81",
        "#00C9A7",
        "#FFC75F",
        "#4CAF50"
    ],

    dataLabels: {
        enabled: true,
        formatter: function (val) {
            return "₹" + Number(val).toLocaleString("en-IN");
        },
        offsetY: -20
    },

    xaxis: {
        categories: monthCategories
    },

    yaxis: {
        labels: {
            formatter: function (val) {
                return "₹" + Number(val).toLocaleString("en-IN");
            }
        }
    },

    tooltip: {
        y: {
            formatter: function (val) {
                return "₹" + Number(val).toLocaleString("en-IN");
            }
        }
    },

    title: {
        text: "Current Month Weekly Income",
        align: "center"
    }
};

new ApexCharts(
    document.querySelector("#mont-chart"),
    options
).render();
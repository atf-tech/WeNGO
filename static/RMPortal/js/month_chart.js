var options = {
    series: [
        {
            name: "Income",
            data: window.monthValues || [],
        },
    ],

    chart: {
        height: 350,
        type: "bar",
        toolbar: {
            show: false,
        },
    },

    plotOptions: {
        bar: {
            borderRadius: 12,
            columnWidth: "50%",
            distributed: true,

            dataLabels: {
                position: "top",
            },
        },
    },

    colors: [
        "#6C63FF",
        "#FF6B81",
        "#00C9A7",
        "#FFC75F",
        "#4D96FF",
        "#B983FF",
        "#FF9671",
    ],

    dataLabels: {
        enabled: true,

        formatter: function (val) {
            return "₹" + Number(val).toLocaleString("en-IN");
        },

        offsetY: -20,

        style: {
            fontSize: "12px",
            fontWeight: "600",
            colors: ["#444"],
        },
    },

    xaxis: {
        categories: window.monthCategories || [],

        axisBorder: {
            show: false,
        },

        axisTicks: {
            show: false,
        },

        labels: {
            rotate: -45,
        },
    },

    yaxis: {
        labels: {
            formatter: function (val) {
                return "₹" + Number(val).toLocaleString("en-IN");
            },
        },
    },

    tooltip: {
        y: {
            formatter: function (val) {
                return "₹" + Number(val).toLocaleString("en-IN");
            },
        },
    },

    title: {
        text: "Current Month Daily Income",
        align: "center",

        style: {
            fontSize: "16px",
            fontWeight: "600",
            color: "#444",
        },
    },
};

var chart = new ApexCharts(
    document.querySelector("#month_chart"),
    options
);

chart.render();
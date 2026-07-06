var options = {
    chart: {
      type: 'bar',
      height: 600,
      toolbar: { show: false }
    },
    series: [{
      name: "collection",
      data: [
        12000, 15000, 8000, 20000, 18000, 22000, 17000, 25000, 30000, 27000,
        23000, 26000, 29000, 31000, 34000, 33000, 36000, 40000, 38000, 42000, 45000
      ]
    }],
    xaxis: {
      categories: [
        "Deepika", "Hema", "Harini", "Rajashalini", "Krishnapriya",
        "Abinaya", "Thameena", "Jennifer", "Pavithra", "Kamalaveni",
        "Durgadevi", "Yamini", "Niranjani", "Pinki", "Pooja",
        "Joy", "Lakshmi", "Hema", "Jothi", "Jayasudha", "Kaviya"
      ],
      title: { text: "All RM's" }
    },
    yaxis: {
      title: { text: "collection (in ₹)" }
    },
    colors: ["#00E396"],
    plotOptions: {
      bar: {
        borderRadius: 4,
        borderRadiusApplication: 'end',
        horizontal: true,
      }
    },
    dataLabels: {
      enabled: true,
      style: { fontSize: "12px", colors: ["#fff"] }
    },
    tooltip: {
      theme: "dark",
      y: {
        formatter: function (val) {
          return "₹ " + val;
        }
      }
    },
    grid: {
      padding: { top: 0, bottom: 0 },
      row: { colors: ["transparent"], opacity: 0 }
    }



  };


  

  var chart = new ApexCharts(document.querySelector("#rmPortalChart"), options);
  chart.render();
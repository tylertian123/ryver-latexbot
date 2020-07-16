function genColors(count) {
    var h = 347;
    var s = 91;
    var l = 54;
    var colors = [];
    for (let i = 0; i < count; i ++) {
        colors.push("hsl(" + ((h + Math.floor(360 / count * i)) % 360) + ", " + s + "%, " + l + "%)");
    }
    return colors;
}
var usageChart = new Chart(document.getElementById("command-usage-chart"), {
    type: "doughnut",
    data: {
        datasets: [{
            data: usageChartData,
            backgroundColor: genColors(usageChartData.length)
        }],
        labels: usageChartLabels
    }
})
function genColors(count, alpha) {
    var h = 347;
    var s = 91;
    var l = 54;
    var colors = [];
    for (let i = 0; i < count; i ++) {
        if (alpha === undefined) {
            colors.push("hsl(" + ((h + 222.5 * i) % 360) + ", " + s + "%, " + l + "%)");
        }
        else {
            colors.push("hsla(" + ((h + 222.5 * i) % 360) + ", " + s + "%, " + l + "%, " + alpha + ")")
        }
    }
    return colors;
}

window.onload = function() {
    var cmdUsageCount = [];
    var cmdNames = [];
    var userCmdUsage = new Map();
    for (cmd in data.commandUsage) {
        cmdNames.push(cmd);
        let uses = 0;
        for (user in data.commandUsage[cmd]) {
            const count = data.commandUsage[cmd][user];
            uses += count;
            if (userCmdUsage.has(user)) {
                userCmdUsage.set(user, userCmdUsage.get(user) + count);
            }
            else {
                userCmdUsage.set(user, count);
            }
        }
        cmdUsageCount.push(uses);
    }

    var usageChartCmd = new Chart(document.getElementById("cmd-usage-cmd"), {
        type: "doughnut",
        data: {
            datasets: [{
                data: cmdUsageCount,
                backgroundColor: genColors(cmdNames.length)
            }],
            labels: cmdNames
        }
    });

    var usageChartUserBar = new Chart(document.getElementById("cmd-usage-user"), {
        type: "bar",
        data: {
            datasets: [{
                label: "Uses",
                data: Array.from(userCmdUsage.values()),
                backgroundColor: genColors(userCmdUsage.size, 0.5)
            }],
            labels: Array.from(userCmdUsage.keys())
        },
        options: {
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true,
                        precision: 0
                    }
                }]
            }
        }
    });
}

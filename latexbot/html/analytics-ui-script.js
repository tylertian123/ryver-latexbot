// Function for generation graph colours
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
    var cmdUsage = [];
    var userCmdUsage = new Map();
    // Tally up various stats
    for (const cmd in data.commandUsage) {
        // Count each user's command usage and usage for every command
        let uses = 0;
        for (const user in data.commandUsage[cmd]) {
            const count = data.commandUsage[cmd][user];
            uses += count;
            if (userCmdUsage.has(user)) {
                userCmdUsage.set(user, userCmdUsage.get(user) + count);
            }
            else {
                userCmdUsage.set(user, count);
            }
        }
        cmdUsage.push([cmd, uses]);
    }
    // Sort the command usage data to only take the top 10
    var usageChartColors;
    cmdUsage = cmdUsage.sort((a, b) => b[1] - a[1])
    if (cmdUsage.length > 10) {
        // Sum up the usage of all commands past 10
        var otherCount = cmdUsage.slice(11).reduce((a, b) => a + b[1], 0);
        cmdUsage = cmdUsage.slice(0, 10);
        cmdUsage.push(["Other", otherCount]);
        // Special fixed colour for Other
        usageChartColors = genColors(cmdUsage.length - 1);
        usageChartColors.push("hsl(0, 0, 54)");
    }
    else {
        usageChartColors = genColors(cmdUsage.length);
    }
    // Sort the user command usage map in descending order and only take the top 20 elements
    userCmdUsage = new Map([...userCmdUsage.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20));

    // Command usage doughnut chart
    var usageChartCmd = new Chart(document.getElementById("cmd-usage-cmd"), {
        type: "doughnut",
        data: {
            datasets: [{
                data: cmdUsage.map((x) => x[1]),
                backgroundColor: usageChartColors
            }],
            labels: cmdUsage.map((x) => x[0])
        }
    });

    // Command usage by user bar chart
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
        // Start y axis at 0
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

    // Count user message activity and take top 20
    var messageActivity = [];
    for (const user in data.messageActivity) {
        messageActivity.push([user, data.messageActivity[user]]);
    }
    messageActivity = messageActivity.sort((a, b) => b[1] - a[1]).slice(0, 20);

    // Message activity bar chart
    var messageActivityChart = new Chart(document.getElementById("msg-activity"), {
        type: "bar",
        data: {
            datasets: [{
                label: "Total message size (characters)",
                data: messageActivity.map(x => x[1]),
                backgroundColor: genColors(messageActivity.length, 0.5),
            }],
            labels: messageActivity.map(x => x[0]),
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

    // Calculate uptime stats
    var uptime = 0;
    var reboots = 0;
    var firstUp;
    var lastUp;
    var lastDown;
    for (let time of data.shutdowns) {
        if (time & 0x1) {
            reboots ++;
            lastUp = time >>> 1;
            if (firstUp === undefined) {
                firstUp = lastUp;
            }
        }
        else {
            lastDown = time >>> 1;
            if (lastUp !== undefined) {
                uptime += lastDown - lastUp;
            }
        }
    }
    if (lastUp !== undefined) {
        uptime += data.timestamp - lastUp;
    }

    var uptimeStats;
    if (reboots <= 1) {
        uptimeStats = "No recorded reboots over a max period of 10 days.<br>"
    }
    else {
        uptimeStats = (reboots - 1) + " recorded reboots over a max period of 10 days.<br>";
    }
    if (data.shutdowns.length > 0) {
        if (lastDown === undefined) {
            uptimeStats += "No shutdowns recorded so far.<br>";
        }
        else {
            uptimeStats += "Last recorded shutdown was at " + new String(new Date(lastDown * 1000)) + ".<br>";
        }
        if (firstUp !== undefined) {
            let total = data.timestamp - firstUp;
            uptimeStats += "LaTeX Bot was up " + (uptime / total * 100).toFixed(3) + "% of the time."
            // Uptime stats doughnut chart
            // Only shown if data actually exists
            var uptimeChart = new Chart(document.getElementById("uptime-stats-chart"), {
                type: "doughnut",
                data: {
                    datasets: [{
                        data: [uptime, total - uptime],
                        backgroundColor: ["hsl(124, 82%, 52%)", "hsl(347, 91%, 54%)"]
                    }],
                    labels: ["Up", "Down"]
                }
            });
        }
        else {
            uptimeStats += "Not enough data to determine uptime percentage."
        }
    }
    document.getElementById("uptime-stats-text").innerHTML = uptimeStats;
}

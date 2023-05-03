google.charts.load('current', {'packages':['bar']});
google.charts.setOnLoadCallback(drawChart);

function drawChart() {

var data_req = jQuery.ajax({
    type: "GET",
    url: "/last_month_comparison",
    async: false
});

data_res = data_req.responseText;

var data = google.visualization.arrayToDataTable([
  ['Category', 'Last Month', 'This Month'],
  ['Rent', 1000, 400],
  ['Utilities', 1170, 460],
  ['Groceries', 660, 1120],
  ['Travel', 1030, 540],
  ['Food', 100, 100],
  ['Ian Savings', 100, 100],
  ['Misc.', 100, 100]
]);

var options = {
  chart: {
    title: 'Last Month Comparison',
  },
  height: 200,
  colors: ['#214E34', '#E09891']
};

var chart = new google.charts.Bar(document.getElementById('last_month_comparison_bar'));

chart.draw(data, google.charts.Bar.convertOptions(options));
}


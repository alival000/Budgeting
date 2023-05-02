// Load the Visualization API and the corechart package.
google.charts.load('current', {'packages':['corechart']});

// Set a callback to run when the Google Visualization API is loaded.
google.charts.setOnLoadCallback(drawChart);

// Callback that creates and populates a data table,
// instantiates the pie chart, passes in the data and
// draws it.
function drawChart() {

// Create the data table.
var data = new google.visualization.DataTable();
data.addColumn('string', 'Topping');
data.addColumn('number', 'Slices');
data.addRows([
  ['Rent', 3],
  ['Utilities', 1],
  ['Groceries', 1],
  ['Travel', 1],
  ['Food', 2],
  ['Ian Savings', 1],
  ['Misc.', 1],
]);

// Set chart options
var options = {'title':'Total Spending This Statement',
               'colors': ['#214E34', '#5C7457', '#979B8D', '#C1BCAC', '#EFD0CA', '#E8B9AB', '#E09891']
              };

// Instantiate and draw our chart, passing in some options.
var chart = new google.visualization.PieChart(document.getElementById('last_statement_pie'));
chart.draw(data, options);
}

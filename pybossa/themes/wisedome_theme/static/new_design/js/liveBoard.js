//$(function () {
    /* ChartJS
     * -------
     * Data and config for chartjs
     */
  //  'use strict';
  
  //신규프로젝트 
    var data = {  
      labels: ["임시 프로젝트", "진행 중 프로젝트","완료 프로젝트"],
      datasets: [{
        label: '프로젝트수',
        data: [1,1,1], 
        backgroundColor: [
          'rgba(255, 99, 132, 0.2)',
          'rgba(54, 162, 235, 0.2)',
          'rgba(255, 206, 86, 0.2)'//,
          //'rgba(75, 192, 192, 0.2)',
          //'rgba(153, 102, 255, 0.2)',
          //'rgba(255, 159, 64, 0.2)'
        ],
        borderColor: [
          'rgba(255,99,132,1)',
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)'//,
          //'rgba(75, 192, 192, 1)',
          //'rgba(153, 102, 255, 1)',
          //'rgba(255, 159, 64, 1)'
        ],
        borderWidth: 1,
        fill: false
      }]
    };

  //최근작업
    var multiColorBar = {  
        labels: ["4월1주", "4월2주","4월3주", "4월4주", "4월5주"],
        datasets: [{
          label: '최근 1주 새로운 작업 수',
          data: [1, 3, 15, 4, 9], 
          backgroundColor: [
            'rgba(255, 99, 132, 0.2)',
            'rgba(54, 162, 235, 0.2)',
            'rgba(255, 206, 86, 0.2)',
            'rgba(75, 192, 192, 0.2)',
            'rgba(153, 102, 255, 0.2)',
            'rgba(255, 159, 64, 0.2)'
          ],
          borderColor: [
            'rgba(255,99,132,1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)'
          ],
          borderWidth: 1,
          fill: false
        }]
      };

//최근답변
    var lineDataSecondary = { 
        labels: ["1주", "2주","3주", "4주", "5주"],
        datasets: [{
          label: '최근 답변',
          data: [1, 3, 7, 4, 3, 9],
          backgroundColor: [
            'rgba(54, 162, 235, 0.2)',
            'rgba(255, 206, 86, 0.5)',
            'rgba(75, 192, 192, 0.5)',
            'rgba(153, 102, 255, 0.5)',
            'rgba(255, 159, 64, 0.5)'
          ],
          borderColor: [
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)'
          ],
          borderWidth: 1,
          fill: true, 
        }]
      };
  
    var options = {
      scales: {
        yAxes: [{
          ticks: {
            beginAtZero: true
          }
        }]
      },
      legend: {
        display: false
      },
      elements: {
        point: {
          radius: 0
        }
      }
  
    };
    var optionsDark = {
      scales: {
        yAxes: [{
          ticks: {
            beginAtZero: true
          },
          gridLines: {
            color: '#322f2f',
            zeroLineColor: '#322f2f'
          }
        }],
        xAxes: [{
          ticks: {
            beginAtZero: true
          },
          gridLines: {
            color: '#322f2f',
          }
        }],
      },
      legend: {
        display: false
      },
      elements: {
        point: {
          radius: 0
        }
      }
  
    };


    //최근활동회원
    var areaData = {
      labels: ["2020년1월", "2020년12월","2021년1월", "2021년2월", "2021년3월", "2021년4월"],
      datasets: [{
          label: '인원수',
          data: [12, 15, 3, 5, 2, 7],
        backgroundColor: [
          'rgba(255, 99, 132, 0.2)',
          'rgba(54, 162, 235, 0.2)',
          'rgba(255, 206, 86, 0.2)',
          'rgba(75, 192, 192, 0.2)',
          'rgba(153, 102, 255, 0.2)',
          'rgba(255, 159, 64, 0.2)'
        ],
        borderColor: [
          'rgba(255,99,132,1)',
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(153, 102, 255, 1)',
          'rgba(255, 159, 64, 1)'
        ],
        borderWidth: 1,
        fill: true, // 3: no fill
      }]
    };
  
    //신규회원
    var areaDataDark = {
      labels: ["2020년1월", "2020년12월","2021년1월", "2021년2월", "2021년3월", "2021년4월"],
      datasets: [{
        label: '가입자수',
        data: [1, 3, 5, 2, 12, 7],
        backgroundColor: [
          'rgba(153, 102, 255, 0.2)',
          'rgba(54, 162, 235, 0.2)',
          'rgba(255, 206, 86, 0.2)',
          'rgba(75, 192, 192, 0.2)',
          'rgba(153, 102, 255, 0.2)',
          'rgba(255, 159, 64, 0.2)'
        ],
        borderColor: [
          'rgba(153, 102, 255, 1)',
          'rgba(255,99,132,1)',
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(255, 159, 64, 1)'
        ],
        borderWidth: 1,
        fill: true, // 3: no fill
      }]
    };
  
    var areaOptions = {
      plugins: {
        filler: {
          propagate: true
        }
      }
    }
  
    var areaOptionsDark = {
      scales: {
        yAxes: [{
          ticks: {
            beginAtZero: true
          },
          gridLines: {
            color: '#322f2f',
            zeroLineColor: '#322f2f'
          }
        }],
        xAxes: [{
          ticks: {
            beginAtZero: true
          },
          gridLines: {
            color: '#322f2f',
          }
        }],
      },
      plugins: {
        filler: {
          propagate: true
        }
      }
    }
  


function mk_chart() {
  
    if ($("#barChart").length) {
      var barChartCanvas = $("#barChart").get(0).getContext("2d");
      var barChart = new Chart(barChartCanvas, {
        type: 'bar',
        data: data,
        options: options
      });
    }
    if ($("#barChart-2").length) {
        var barChartCanvas = $("#barChart-2").get(0).getContext("2d");

        var barChart = new Chart(barChartCanvas, {
          type: 'bar',
          data: multiColorBar,
          options: options
        });
      }
    
  
    if ($("#lineChart").length) {
      var lineChartCanvas = $("#lineChart").get(0).getContext("2d");
      var lineChart = new Chart(lineChartCanvas, {
        type: 'line',
        data: data,
        options: options
      });
    }

    if ($("#lineChart-2").length) {
        var lineChartCanvas = $("#lineChart-2").get(0).getContext("2d");
        var lineChart = new Chart(lineChartCanvas, {
          type: 'line',
          data: lineDataSecondary,
          options: options
        });
      }
    
  
    if ($("#areaChart").length) {
      var areaChartCanvas = $("#areaChart").get(0).getContext("2d");
      var areaChart = new Chart(areaChartCanvas, {
        type: 'line',
        data: areaData,
        options: areaOptions
      });
    }

    if ($("#areaChart-2").length) {
        var areaChartCanvas = $("#areaChart-2").get(0).getContext("2d");
        var areaChart = new Chart(areaChartCanvas, {
          type: 'line',
          data: areaDataDark,
          options: areaOptions
        });
      }
}
  
  //});

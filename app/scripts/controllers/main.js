'use strict';

/**
 * @ngdoc function
 * @name osApiDocApp.controller:MainCtrl
 * @description
 * # MainCtrl
 * Controller of the osApiDocApp
 */
angular.module('osApiDocApp')
  .controller('MainCtrl', function ($scope, $http, $sce) {
    $scope.awesomeThings = [
      'HTML5 Boilerplate',
      'AngularJS',
      'Karma'
    ];
  $http.get('http://localhost:8776/docs/v1/').
    success(function(data, status, headers, config) {
      $scope.apis = data;
    }).
    error(function(data, status, headers, config) {
      // log error
    });
  });

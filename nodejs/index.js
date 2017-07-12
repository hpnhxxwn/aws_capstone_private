

require('dotenv').load();

// - get command line arguments
var argv = require('minimist')(process.argv.slice(2));
var port = argv['port'];
var redis_host = argv['redis_host'];
var redis_port = argv['redis_port'];
var redis_channel = argv['redis_channel'];

// - setup dependency instances
var express = require('express');
var app = express();
// var http = require('http').Server(app); // var server = require('http').createServer(app);
var server = require('http').createServer(app);
var path = require('path');
// var io = require('socket.io')(http);
var io = require('socket.io')(server);
var Twitter = require('twitter');
var havenondemand = require('havenondemand');

// - setup redis client
var redis = require('redis');
console.log('Creating a redis client');
var redisClient = redis.createClient(redis_port, redis_host);
redisClient.subscribe(redis_channel);
console.log('Subscribing to redis channel %s', redis_channel);

// when new message arrives, invoke function
redisClient.on('message', function (channel, message) {
    if (channel == redis_channel) {
        console.log('message received %s', message);
        io.sockets.emit('data', message);
    }
});

// - setup webapp routing
app.use('/', express.static(__dirname + '/views'));
app.use(express.static(__dirname + '/views'));
app.use('/jquery', express.static(__dirname + '/node_modules/jquery/dist/'));
app.use('/d3', express.static(__dirname + '/node_modules/d3/'));
app.use('/nvd3', express.static(__dirname + '/node_modules/nvd3/build/'));
app.use('/bootstrap', express.static(__dirname + '/node_modules/bootstrap/dist'));





var hodClient = new havenondemand.HODClient('f9eb07d3-7c67-4550-8583-a1bd8f7826d3', version="v2")

var twitterClient = new Twitter({
  consumer_key: 'cNFkNf61GS13k28VVPg8Gqmcm',
  consumer_secret: 'cQbeDBXaiUyC4A3V2kATC56l5CdVFsT6kWSKDuJXGQUyEIiLLC',
  access_token_key: '2482588262-qiDrxYC0AnPyofpZWvUIZtXmXYVJvkwoKtm3TNC',
  access_token_secret: 'MVuVx4rlyuw9z6MKlv3IOvjky0GWuGE02qkHxgXZ4IsBh'
});

// port = process.env.PORT || 3000;
port = 5000;
app.use(express.static(path.join(__dirname, 'public')));

newAverage = 0;
oldAverage = 0;
n = 0;

// io.on('streamTopic', function(msg){
//   console.log(msg)
// })

io.on('connection', function(socket){

  socket.on('disconnect', function () {
    socket.emit('user disconnected');
  });

  socket.on('streamTopic', function(msg){
    newAverage = 0;
    oldAverage = 0;
    n = 0;
    console.log(msg);

    twitterClient.stream('statuses/filter', {track: msg.topic}, function(stream) {
      stream.on('data', function(tweet) {
        var data = {text: tweet.text};
        console.log(data);
        hodClient.post('analyzesentiment', data, false, function(err, resp, body){
          if (!err) {
            console.log(resp.body);
            if (resp.body.sentiment_analysis[0].aggregate !== undefined) {
              var analysis = resp.body.sentiment_analysis[0];
              n += 1; //increase n by one
              var sentiment = analysis.aggregate.sentiment;
              var score = analysis.aggregate.score;
              newAverage = calculateRunningAverage(score, n);
              rgbInstantaneous = mapColor(score);
              rgbAverage = mapColor(newAverage);
              console.log("------------------------------");
              console.log(tweet.text + " | " + sentiment + " | " + score);
              var tweetData = {tweet: tweet, positive: analysis.positive, negative: analysis.negative, aggregate: analysis.aggregate, rgbInstantaneous: rgbInstantaneous, rgbAverage: rgbAverage, average: newAverage};
              io.emit('tweetData', tweetData);
              console.log("tweet send back to UI");
            }
          }
        });
      });

      stream.on('disconnect', function (disconnectMessage) {
        console.log(disconnectMessage);
      });

      stream.on('error', function(error) {
        throw error;
      });
    });

  });

});

app.get("/", function(req, res){
  res.sendFile(__dirname + '/views/index.html');
});

// http.listen(port, function(){
//   console.log("Server started listening at port: "+port);
// });
server.listen(3000, function () {
   console.log('Server started listening at port %d.', 3000);
});

mapColor = function (score) {
  weight = Math.floor(((0.5*score + 0.5)*100));
  r = Math.floor( (255 * (100 - weight)) / 100 );
  g = Math.floor( (255 * weight) / 100 );
  b = 0;
  return {r: r, g: g, b:b};
}

calculateRunningAverage = function(score, n) {
  newAverage = oldAverage * (n-1)/n + score/n;   // New average = old average * (n-1)/n + new value /n
  oldAverage = newAverage; //set equal to new average for next go around of calling this function
  return newAverage;
}






// - setup shutdown hooks
var shutdown_hook = function () {
    console.log('Quitting redis client');
    redisClient.quit();
    console.log('Shutting down app');
    process.exit();
};

process.on('SIGTERM', shutdown_hook);
process.on('SIGINT', shutdown_hook);
process.on('exit', shutdown_hook);





/* jshint globalstrict:true, esnext:true, node:true */
"use strict";

//run server with nodejs --harmony ddrop.js
//or with sudo systemctl restart ddrop (if you've installed ddrop.service)
//logs via stdout or journalctl -u ddrop -f

const addr='192.168.1.174', port = 19861;
const output_folder='stats_reported';

const fs = require('fs');
const http = require('http');

if (!fs.existsSync(output_folder)){
	fs.mkdirSync(output_folder);
}

// Configure our HTTP server to respond with Hello World to all requests.
const server = http.createServer(function (req, res) {
	console.info('' + Date() + ': handling ' + req.method + ' from ' + req.headers.host);
	
	if(req.method === "POST") {
		let data = '';
		req.on('data', function(dat) { data += dat; }); //implement limits here if dos issues
		req.on('end', function() {
			console.log('got', data)
			let fields = JSON.parse(data);
			if(!fields.tag) { console.error('missing tag'); }
			if(!fields.serial_number) { console.error('missing serial_number'); }
			
			fields.timestamp =  (new Date()).toUTCString();
			fs.appendFileSync(`${output_folder}/${fields.tag}.jsonl`, JSON.stringify(fields)+'\n');
			res.writeHead(200, {"Content-Type": "text"});
			res.end('ok');
		});
	} else {
		interfaceHTML = fs.readFileSync('stats.html', 'utf8');
		res.writeHead(200, {"Content-Type": "text/html"});
		res.end(e, interfaceHTML);
	}
});

//listen for incoming connections
server.listen(port, addr);
console.log("Server running at http://"+addr+":"+port+"/");

//don't die on errors
process.on('uncaughtException', function (err) {
	console.error(err.stack);
});
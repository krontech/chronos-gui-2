/* jshint globalstrict:true, esnext:true, node:true */
"use strict";

//run server with:
//	nohup node stats.node.js & disown
//watch files with:
//	ls stats\.* | entr scp stats\.* stats:camera_stats/

const addr='192.168.1.55', port = 19861;
const output_folder='stats_reported';

const fs = require('fs');
const http = require('http');

console.log("Running stats server at http://"+addr+":"+port+"/");

if (!fs.existsSync(output_folder)){
	console.log(`Making output folder at ${output_folder}.`)
	fs.mkdirSync(output_folder);
}

//after setup, don't die on errors
process.on('uncaughtException', function (err) {
	console.error(err.stack);
});


const server = http.createServer(function (req, res) {
	console.info('' + Date() + ': handling ' + req.method + ' from ' + req.headers.host);
	
	if(req.method === 'POST' && req.url === '/') {
		let data = '';
		req.on('data', function(dat) {
			data += dat;
			if(data.length > 2000) { 
				console.error('Request too long.')
				req.abort()
				res.writeHead(403, {"Content-Type": "text"});
				res.end('{"error": "#KIL8cK"}', 'utf8'); //Request too long.
			}
		});
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
	} 
	
	else if(req.method === 'GET' && req.url === '/') {
		const interfaceHTML = fs.readFileSync('stats.html', 'utf8');
		res.writeHead(200, {"Content-Type": "text/html"});
		res.end(interfaceHTML, 'utf8');
	} 
	
	else if(req.method === 'GET' && req.url === '/start_up_time.jsonl') {
		const data = fs.readFileSync(`${output_folder}/start_up_time.jsonl`, 'utf8');
		res.writeHead(200, {"Content-Type": "text/jsonl"});
		res.end(data, 'utf8');
	} 
	
	else if(req.method === 'GET' && req.url === '/screen_cache_time.jsonl') {
		const data = fs.readFileSync(`${output_folder}/screen_cache_time.jsonl`, 'utf8');
		res.writeHead(200, {"Content-Type": "text/jsonl"});
		res.end(data, 'utf8');
	} 
	
	else {
		res.writeHead(404, {"Content-Type": "text/jsonl"});
		res.end('{"error": "404 not found"}', 'utf8');
	}
})
server.listen(port, addr);
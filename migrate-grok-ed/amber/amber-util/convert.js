//const { convertHtmlToAmber } = require('./index.js');

//const fs = require('fs');
import { convertHtmlToAmber } from './index.js';
import * as fs from 'fs';


// print all the command line arguments
process.argv.forEach(function (val, index, array) {
    console.log(index + ': ' + val);
});

// quit if there are not three command line arguments
if (process.argv.length < 3) {
    console.log('Usage: node convert.js input.html output.html');
    process.exit(1);
}


// print an error and exit if the input file does not exist
if (!fs.existsSync(process.argv[2])) {
    console.log('Input file ' + process.argv[2] + ' does not exist\n');
    process.exit(1);
}



fs.readFile(process.argv[2], 'utf8', (err, data) => {
    if (err) {
        console.error(err);
        return;
    }
    var ctx = convertHtmlToAmber(data);
    fs.writeFileSync(process.argv[3], ctx);
});

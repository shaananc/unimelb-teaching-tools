//const { HtmlDocumentFormat } = require('./HTMLDocumentFormat');
import { HtmlDocumentFormat } from './HTMLDocumentFormat.js';
//const { documentToXml } = require('./DocumentFormat');
import { documentToXml } from './DocumentFormat.js';

function convertHtmlToAmber(html) {
  const doc = new HtmlDocumentFormat().convert(html);
  return documentToXml(doc);
}

//exports.convertHtmlToAmber = convertHtmlToAmber;
export { convertHtmlToAmber };
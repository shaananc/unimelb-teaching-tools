//const { JSDOM } = require('jsdom');
import { JSDOM } from 'jsdom';

//const { DocumentBuilder } = require('./DocumentBuilder');
import { DocumentBuilder } from './DocumentBuilder.js';

const rejectedTags = new Set([
    'COL',
    'META',
    'TEMPLATE',
    'HEAD',
    'TITLE',
    'SCRIPT',
]);
const blockTags = new Set([
    'ADDRESS',
    'ARTICLE',
    'ASIDE',
    'BLOCKQUOTE',
    'DETAILS',
    'DIALOG',
    'DD',
    'DIV',
    'DL',
    'DT',
    'FIELDSET',
    'FIGCAPTION',
    'FIGURE',
    'FOOTER',
    'FORM',
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
    'HEADER',
    'HGROUP',
    'HR',
    'LI',
    'MAIN',
    'NAV',
    'OL',
    'P',
    'PRE',
    'SECTION',
    'TABLE',
    'UL',
]);
function isElementOnNewLine(el) {
    // Must be block element
    if (!blockTags.has(el.tagName)) {
        return false;
    }
    // If the concatenated text content of all previous siblings is whitespace
    // then it does not cause a new line
    const prevNodes = [];
    for (let node = el.previousSibling; node; node = node.previousSibling) {
        prevNodes.unshift(node);
    }
    if (!prevNodes.reduce((text, n) => text + n.textContent, '').trim()) {
        return false;
    }
    return true;
}
function createWalker(window, node) {
    const { Node, NodeFilter } = window;
    const nodeFilter = {
        acceptNode(node) {
            // Reject custom elements that Microsoft Word inserts
            return node.nodeType !== Node.ELEMENT_NODE || (!node.tagName.includes(':') &&
                !rejectedTags.has(node.tagName))
                ? NodeFilter.FILTER_ACCEPT
                : NodeFilter.FILTER_REJECT;
        },
    };

    return window.document.createTreeWalker(node, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, nodeFilter);
}
class HtmlDocumentFormat {
    convert(content) {
        this.dom = new JSDOM(content);
        this.window = this.dom.window;
        this.htmlDoc = this.window.document;
        this.walker = createWalker(this.window, this.htmlDoc.body);
        this.builder = new DocumentBuilder();
        this.significantWhitespace = false;
        this.parse(this.htmlDoc.body);
        const doc = this.builder.document;
        this.htmlDoc = null;
        this.walker = null;
        this.builder = null;
        return doc;
    }
    parse(el, options = null) {
        const { Node } = this.window;

        // TODO:
        // There are ranges of whitespace that we should collapse or remove entirely.
        // Leading whitespace after the open tag and trailing whitespace before the
        // closing tag of block elements should be removed:
        //
        // <div>   text   </div>
        // <div>text </div>
        //
        // <div> <b> </b> <i> </i> text <b> </b> </div>
        // <div><b></b><i></i>text <b></b></div>
        //
        // Empty elements will be stripped out.
        // Other ranges of whitespace should be collapsed into a single space:
        //
        // <div>hello  <b>   bold   </b>  world</div>
        // <div>hello <b>bold </b>world</div>
        //
        // We need to keep track of the text we have seen since the beginning of
        // a block element.
        const oldSignificantWhitespace = this.significantWhitespace;
        // getComputedStyle on a detached element or an element from a non-visible
        // document will return empty computed styles in WebKit and Chrome
        if (el.tagName === 'PRE') {
            this.significantWhitespace = true;
        }
        // Replace the walker with a new local walker for this subtree
        const oldWalker = this.walker;
        this.walker = createWalker(this.window, el);
        for (; ;) {
            const node = this.walker.nextNode();
            if (!node) {
                break;
            }
            if (node.nodeType === Node.TEXT_NODE) {
                this.visitText(node);
                continue;
            }
            const el = node;
            switch (el.tagName) {
                case 'P':
                    this.visitParagraph(el);
                    break;
                case 'OL':
                case 'UL':
                    this.visitList(el);
                    break;
                case 'LI':
                    this.visitListItem(el);
                    break;
                case 'H1':
                case 'H2':
                case 'H3':
                case 'H4':
                case 'H5':
                case 'H6':
                    this.visitHeading(el);
                    break;
                case 'BLOCKQUOTE':
                    this.visitBlockquote(el);
                    break;
                case 'PRE':
                    this.visitPre(el);
                    break;
                case 'BR':
                    this.visitBreak(el);
                    break;
                case 'B':
                case 'STRONG':
                    this.visitBasicAnnotation(el, 'bold');
                    break;
                case 'I':
                case 'EM':
                    this.visitBasicAnnotation(el, 'italic');
                    break;
                case 'U':
                    this.visitBasicAnnotation(el, 'underline');
                    break;
                case 'CODE':
                    this.visitBasicAnnotation(el, 'code');
                    break;
                case 'S':
                case 'DEL':
                case 'STRIKE':
                    this.visitBasicAnnotation(el, 'strike');
                    break;
                case 'A':
                    this.visitAnchor(el);
                    break;
                default: {
                    if (blockTags.has(el.tagName)) {
                        this.visitGeneralBlockElement(el);
                    }
                }
            }
        }
        // Restore the old walker at the same position as the current walker
        // so we can continue at the same point
        oldWalker.currentNode = this.walker.currentNode;
        this.walker = oldWalker;
        this.significantWhitespace = oldSignificantWhitespace;
    }
    visitGeneralBlockElement(el) {
        if (this.builder.significantWhitespace) {
            // Only append a newline if this div would result in a new line
            if (isElementOnNewLine(el)) {
                this.builder.appendText('\n');
            }
        }
        else {
            if (!this.builder.isContentBranchEmpty()) {
                this.visitParagraph(el);
            }
        }
    }
    visitParagraph(el) {
        this.builder.appendParagraph();
        this.parse(el);
        this.builder.endContentBranch();
    }
    visitCode(el) {
        this.builder.appendCode();
        this.parse(el);
        this.builder.endContentBranch();
    }
    visitPre(el) {
        // check if el has a child of code type
        let code = el.querySelector('code');
        let lang = '';
        if (code) {
            let eclass = code.getAttribute('class');
            // if the class name starts with 'language-' then extract the language
            // name and add it as an annotation
            if (eclass && eclass.startsWith('language-')) {
                lang = eclass.substring(9);
                console.log("extracted language: " + lang);
            }
        }


        this.builder.appendPre(lang);
        this.parse(el);
        this.builder.endContentBranch();
    }
    visitHeading(el) {
        const level = +el.tagName.match(/H([1-6])/)[1];
        this.builder.appendHeading(level);
        this.parse(el);
        this.builder.endContentBranch();
    }
    visitBlockquote(el) {
        this.builder.pushBlockquote();
        this.parse(el);
        this.builder.popBlockquote();
    }
    visitBreak(el) {
        this.builder.appendText('\n');
    }
    visitList(el) {
        const style = el.tagName === 'OL' ? 'ordered' : 'unordered';
        this.builder.appendList(style);
        this.parse(el);
        this.builder.endList();
    }
    visitListItem(el) {
        this.builder.appendListItem();
        this.parse(el);
        this.builder.endListItem();
    }
    visitBasicAnnotation(el, annotation) {
        // Disallow inline code inside code blocks
        if (annotation === 'code' && this.builder.significantWhitespace) {
            this.parse(el);
        }
        else {
            this.builder.pushBasicAnnotation(annotation);

            this.parse(el);
            this.builder.popAnnotation();
        }
    }
    visitAnchor(el) {
        this.builder.pushLinkAnnotation(el.getAttribute('href'));
        this.parse(el);
        this.builder.popAnnotation();
    }
    visitText(node) {
        let text = node.nodeValue;
        if (!this.significantWhitespace) {
            // Skip text that is completely whitespace and contains a newline
            if (text.match(/^\s*$/) && text.match(/\n/)) {
                return;
            }
            // Collapse consecutive whitespace into a single space
            text = text.replace(/\s+/g, ' ');
        }
        this.builder.appendText(text);
    }
}

//exports.HtmlDocumentFormat = HtmlDocumentFormat;
export { HtmlDocumentFormat }
//const { JSDOM } = require('jsdom');
import { JSDOM } from 'jsdom';
const dom = new JSDOM();
import { decode } from 'html-entities';


class XmlRenderer {
    render(doc) {
        this.xmlDoc = dom.window.document.implementation.createDocument(null, 'document', null);
        this.xmlDoc.documentElement.setAttribute('version', '2.0');
        this.current = this.xmlDoc.documentElement;
        for (const child of doc.children) {
            this.renderNode(child);
        }
        return this.xmlDoc;
    }
    renderNode(n, options = false) {
        if (options && options.inCode) {
            if (n.type === 'text') {
                this.renderText(n, { 'inCode': 'true' });
                return;
            }
            else {
                if (!n.children) { return; }
                for (const child of n.children) {
                    this.renderNode(child, { 'inCode': 'true' });
                }
                return;
            }
        }
        switch (n.type) {
            case 'paragraph':
                this.renderParagraph(n);
                break;
            case 'heading':
                this.renderHeading(n);
                break;
            case 'blockquote':
                this.renderBlockquote(n);
                break;
            case 'code':
                this.renderCode(n);
                break;
            case 'list':
                this.renderList(n);
                break;
            case 'listItem':
                this.renderListItem(n);
                break;
            case 'text':
                this.renderText(n);
                break;
            case 'break':
                this.renderBreak(n);
                break;
            case 'annotation':
                this.renderAnnotation(n);
                break;
            case 'pre':
                this.renderPre(n);
                break;
        }
    }
    renderParagraph(p) {
        const el = this.xmlDoc.createElement('paragraph');
        this.current.appendChild(el);
        this.current = el;
        for (const child of p.children) {
            this.renderNode(child);
        }
        this.current = this.current.parentElement;
    }
    renderHeading(h) {
        const el = this.xmlDoc.createElement('heading');
        el.setAttribute('level', h.level.toString());
        // TODO remove
        console.log("REMOVING ALL H1 Elements!")
        if (h.level === 1) {
            return;
        }


        this.current.appendChild(el);
        this.current = el;
        for (const child of h.children) {
            this.renderNode(child);
        }
        this.current = this.current.parentElement;
    }
    renderBlockquote(b) {
        const el = this.xmlDoc.createElement('callout');
        el.setAttribute('type','info')
        this.current.appendChild(el);
        this.current = el;
        for (const child of b.children) {
            this.renderNode(child);
        }
        this.current = this.current.parentElement;
    }
    renderCode(c) {
        // this is the big to fix
        const el = this.xmlDoc.createElement('pre');

        this.current.appendChild(el);
        this.current = el;

        for (const child of c.children) {
            this.renderNode(child);
        }
        this.current = this.current.parentElement;
    }
    renderPre(c) {
        // Begin Shaanan Code
        const el = this.xmlDoc.createElement('snippet');
        if (c.lang) {
            el.setAttribute('language', c.lang);
        } else {
            el.setAttribute('language', 'bash');
        }
        el.setAttribute('runnable', 'true');
        el.setAttribute('line-numbers', 'true');
        // End Shaanan Code
        this.current.appendChild(el);
        this.current = el;

        for (const child of c.children) {
            this.renderNode(child, { 'inCode': 'true' });
        }
        this.current = this.current.parentElement;
    }

    renderList(l) {
        const el = this.xmlDoc.createElement('list');
        el.setAttribute('style', l.style);
        this.current.appendChild(el);
        this.current = el;
        for (const child of l.children) {
            this.renderNode(child);
        }
        this.current = this.current.parentElement;
    }
    renderListItem(i) {
        const el = this.xmlDoc.createElement('list-item');
        this.current.appendChild(el);
        this.current = el;
        for (const child of i.children) {
            this.renderNode(child);
        }
        this.current = this.current.parentElement;
    }
    renderText(t, options) {
        if (options && options.inCode) {
            let text = decode(t.value) + '\n';
            this.current.appendChild(this.xmlDoc.createTextNode(text));
            return;
        } else {
            this.current.appendChild(this.xmlDoc.createTextNode(t.value));
        }
    }
    renderBreak(b) {
        this.current.appendChild(this.xmlDoc.createElement('break'));
    }

    renderAnnotation(a) {
        let el;
        if (a.annotation === 'link') {
            el = this.xmlDoc.createElement('link');
            el.setAttribute('href', a.url);
        }
        else {
            el = this.xmlDoc.createElement(a.annotation);
        }
        this.current.appendChild(el);
        this.current = el;
        for (const child of a.children) {
            this.renderNode(child);
        }
        this.current = this.current.parentElement;
    }
}

function documentToXml(doc) {
    const xmlDoc = new XmlRenderer().render(doc);
    return new dom.window.XMLSerializer().serializeToString(xmlDoc);
}

//exports.documentToXml = documentToXml;
export { documentToXml }
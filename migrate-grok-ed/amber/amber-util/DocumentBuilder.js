
class DocumentBuilder {
    constructor() {
        this.document = {
            type: 'document',
            children: [],
        };
        this.branchStack = [];
        this.branch = this.document;
        this.contentBranchStack = [];
        this.contentBranch = null;
        this.blockquoteLevel = 0;
    }
    get significantWhitespace() {
        return this.contentBranch?.type === 'code';
    }
    appendText(s) {
        if (!s) {
            return;
        }
        const b = this.ensureContentBranch();
        const lines = s.split(/\r?\n/);
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].replace(/\t/g, '    ');
            const lastChild = b.children[b.children.length - 1];
            if (lastChild?.type === 'text') {
                // Append to the last child
                lastChild.value += line;
            }
            else {
                // Create a new text node
                b.children.push({
                    type: 'text',
                    value: line,
                });
            }
            if (i < lines.length - 1) {
                if (this.significantWhitespace) {
                    b.children[b.children.length - 1].value += '\n';
                }
                else {
                    b.children.push({ type: 'break' });
                }
            }
        }
    }
    appendParagraph() {
        const b = this.applyBlockquote() || {
            type: 'paragraph',
            children: [],
        };
        this.branch.children.push(b);
        this.contentBranch = b;
    }
    appendHeading(level) {
        const b = this.applyBlockquote() || {
            type: 'heading',
            level,
            children: [],
        };
        this.branch.children.push(b);
        this.contentBranch = b;
    }
    appendCode() {
        const c = {
            type: 'code',
            children: [],
        };
        this.branch.children.push(c);
        this.contentBranch = c;
    }
    appendPre(lang) {
        const c = {
            type: 'pre',
            children: [],
            lang: lang,
        };
        this.branch.children.push(c);
        this.contentBranch = c;
    }


    appendList(style) {
        // Lists can only be appended to Document and ListItem nodes
        while (this.branch.type !== 'document' && this.branch.type !== 'listItem' && this.branch.type !== 'list') {
            this.popBranch();
        }
        // If we are directly inside a List (but not a ListItem) then implicitly
        // create a ListItem so that we can append the List to it
        if (this.branch.type === 'list') {
            this.appendListItem();
        }
        this.pushBranch({
            type: 'list',
            style,
            children: [],
        });
    }
    appendListItem() {
        // ListItem can only be appended to List node
        this.ensureList();
        this.pushBranch({
            type: 'listItem',
            children: [],
        });
    }
    pushBlockquote() {
        this.blockquoteLevel++;
        this.endContentBranch();
    }
    popBlockquote() {
        this.blockquoteLevel--;
        this.endContentBranch();
    }
    applyBlockquote() {
        return this.blockquoteLevel > 0
            ? {
                type: 'blockquote',
                children: [],
            }
            : null;
    }
    pushBranch(b) {
        this.branch.children.push(b);
        this.branchStack.push(this.branch);
        this.branch = b;
        this.endContentBranch();
    }
    popBranch() {
        this.branch = this.branchStack.pop();
        this.endContentBranch();
    }
    pushBasicAnnotation(annotation) {
        this.pushAnnotation({
            type: 'annotation',
            annotation,
            children: [],
        });
    }
    pushLinkAnnotation(url) {
        this.pushAnnotation({
            type: 'annotation',
            annotation: 'link',
            url,
            children: [],
        });
    }
    pushAnnotation(a) {
        const top = this.ensureContentBranch();
        top.children.push(a);
        this.contentBranchStack.push(top);
        this.contentBranch = a;
    }
    popAnnotation() {
        this.contentBranch = this.contentBranchStack.pop();
    }
    endList() {
        while (this.branch.type === 'list') {
            this.popBranch();
        }
    }
    endListItem() {
        while (this.branch.type === 'listItem') {
            this.popBranch();
        }
    }
    ensureList(style = 'unordered') {
        // Break out to the closest list parent
        while (this.branch.type !== 'document' && this.branch.type !== 'list') {
            this.popBranch();
        }
        // At we at a list?
        if (this.branch.type === 'list') {
            return this.branch;
        }
        // Append a new list
        const l = {
            type: 'list',
            style,
            children: [],
        };
        this.pushBranch(l);
        return l;
    }
    ensureContentBranch() {
        if (!this.contentBranch) {
            this.appendParagraph();
        }
        return this.contentBranch;
    }
    endContentBranch() {
        this.contentBranch = null;
        this.contentBranchStack = [];
    }
    isContentBranchEmpty() {
        return this.contentBranch?.children.length === 0;
    }
}

//exports.DocumentBuilder = DocumentBuilder;
export { DocumentBuilder };
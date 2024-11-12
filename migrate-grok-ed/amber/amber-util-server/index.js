const Koa = require('koa');
const Router = require('@koa/router');
const bodyParser = require('koa-bodyparser');
const { convertHtmlToAmber } = require('amber-util');

const app = new Koa();
const router = new Router();

router.post('/convert', ctx => {
  ctx.assert(ctx.request.is('text/*'), 415, 'Content-Type must be text/html or text/plain.');
  ctx.body = convertHtmlToAmber(ctx.request.body);
});

app
  .use(bodyParser({
    enableTypes: ['text'],
    extendTypes: {
      text: 'text/html',
    },
  }))
  .use(router.routes())
  .use(router.allowedMethods());

const port = process.env.PORT || 3000;
app.listen(port);
console.log(`Listening on port ${port}`);

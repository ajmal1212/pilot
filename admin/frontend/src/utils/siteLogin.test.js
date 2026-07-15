import assert from 'node:assert/strict'
import test from 'node:test'

import { openSiteLogin } from './siteLogin.js'


function installBrowser() {
  const events = []
  const popup = {
    opener: {},
    close: () => events.push('close'),
  }
  const form = {
    append: (input) => events.push(['input', input]),
    submit: () => events.push('submit'),
    remove: () => events.push('remove'),
  }

  global.window = {
    crypto: { randomUUID: () => 'handoff-id' },
    open: (url, target) => {
      events.push(['open', url, target])
      return popup
    },
  }
  global.document = {
    createElement: (tag) => (tag === 'form' ? form : {}),
    body: { append: () => events.push('append') },
  }
  return { events, popup, form }
}


test('posts a login handoff through a pre-opened window', async () => {
  const { events, popup, form } = installBrowser()
  const link = {
    method: 'POST',
    url: 'http://site.localhost:7000/api/v1/site-login-handoffs',
    handoff_token: 'one-time-token',
  }

  await openSiteLogin(async () => {
    events.push('request')
    return link
  })

  assert.deepEqual(events[0], ['open', '', 'site-login-handoff-id'])
  assert.equal(events[1], 'request')
  assert.equal(popup.opener, null)
  assert.equal(form.method, 'POST')
  assert.equal(form.action, link.url)
  assert.equal(form.target, 'site-login-handoff-id')
  assert.deepEqual(events[2], [
    'input',
    { type: 'hidden', name: 'handoff_token', value: 'one-time-token' },
  ])
  assert.deepEqual(events.slice(3), ['append', 'submit', 'remove'])
})


test('closes the pre-opened window when link creation fails', async () => {
  const { events } = installBrowser()

  await assert.rejects(
    openSiteLogin(async () => {
      throw new Error('failed')
    }),
    /failed/,
  )

  assert.equal(events.at(-1), 'close')
})

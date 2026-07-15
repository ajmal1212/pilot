export async function openSiteLogin(createLink) {
  const target = `site-login-${window.crypto.randomUUID()}`
  const popup = window.open('', target)
  if (!popup) throw new Error('Allow pop-ups to open the site.')
  popup.opener = null

  try {
    const link = await createLink()
    submitSiteLogin(link, target)
    return link
  } catch (error) {
    popup.close()
    throw error
  }
}

function submitSiteLogin(link, target) {
  if (
    link?.method !== 'POST'
    || typeof link.url !== 'string'
    || typeof link.handoff_token !== 'string'
  ) {
    throw new Error('The site login handoff is invalid.')
  }

  const form = document.createElement('form')
  form.method = 'POST'
  form.action = link.url
  form.target = target

  const token = document.createElement('input')
  token.type = 'hidden'
  token.name = 'handoff_token'
  token.value = link.handoff_token
  form.append(token)

  document.body.append(form)
  form.submit()
  form.remove()
}

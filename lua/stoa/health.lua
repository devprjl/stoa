local M = {}

function M.check()
  local health = vim.health
  local store = require 'stoa.store'
  health.start 'stoa.nvim'

  if vim.fn.has 'nvim-0.10' == 1 then
    health.ok 'Neovim 0.10 or newer'
  else
    health.error 'Neovim 0.10 or newer is required'
  end

  local bundled = store.read(store.bundled() .. '/index.json')
  if bundled then
    health.ok(('bundled pack %s with %s quotes'):format(bundled.version or '?', bundled.quotes or '?'))
  else
    health.error 'bundled data is missing, reinstall the plugin'
  end

  local dir, index = store.pack()
  health.info(('active pack: %s (%s)'):format(index.version or '?', dir == store.bundled() and 'bundled' or 'synced'))

  if vim.fn.executable 'curl' == 1 then
    health.ok 'curl found, background sync available'
  else
    health.warn 'curl not found, quotes stay on the bundled pack'
  end

  local state = store.state()
  if state.last_attempt then health.info(('last sync %s: %s'):format(os.date('%Y-%m-%d %H:%M', state.last_attempt), state.last_result or '')) end
end

return M

if vim.g.loaded_stoa then return end
vim.g.loaded_stoa = true

local actions = { show = 'show', next = 'next', home = 'home', notify = 'notify', copy = 'copy', sync = 'sync', info = 'info' }

local function run(args)
  local name = args.fargs[1] or 'show'
  local stoa = require 'stoa'
  if not actions[name] then return vim.notify('Unknown Stoa command: ' .. name, vim.log.levels.WARN, { title = 'stoa' }) end
  if name == 'next' then
    stoa.next()
    return stoa.show()
  end
  stoa[name]()
end

local function complete(lead)
  local names = vim.tbl_keys(actions)
  table.sort(names)
  return vim.tbl_filter(function(name) return name:find(lead, 1, true) == 1 end, names)
end

vim.api.nvim_create_user_command('Stoa', run, { nargs = '?', complete = complete, desc = 'Show a quote with matching art' })
vim.api.nvim_create_user_command('Quote', run, { nargs = '?', complete = complete, desc = 'Show a quote with matching art' })

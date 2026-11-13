local config = require 'stoa.config'
local picker = require 'stoa.picker'
local store = require 'stoa.store'

local M = {}

local current
local prepared = false

local fallback = {
  id = 'fallback',
  text = 'The impediment to action advances action. What stands in the way becomes the way.',
  author = 'Marcus Aurelius',
  work = 'Meditations',
  category = 'philosophy',
}
fallback.art = require('stoa.generate').art(fallback.id)

local function valid(quote) return picker.allowed(quote) and type(quote.art) == 'table' end

local function prepare()
  if prepared then return end
  prepared = true
  vim.defer_fn(function()
    local ok, quote = pcall(picker.pick, current and current.id)
    if ok and quote then store.write(store.state_path 'next.json', quote) end
    pcall(function() require('stoa.sync').maybe() end)
  end, 1500)
end

function M.setup(opts)
  config.setup(opts)
  if not config.options.quote_command then pcall(vim.api.nvim_del_user_command, 'Quote') end
  if config.options.dashboard then require('stoa.dashboard').enable() end
end

function M.current()
  if current then return current end
  local path = store.state_path 'next.json'
  local ok, quote = pcall(store.read, path)
  if ok and valid(quote) then
    store.remove(path)
  else
    ok, quote = pcall(picker.pick)
    if not ok then quote = nil end
  end
  current = quote or fallback
  prepare()
  return current
end

function M.next()
  local ok, quote = pcall(picker.pick, current and current.id)
  current = ok and quote or current or fallback
  prepare()
  return current
end

function M.attribution(quote) return require('stoa.render').attribution(quote or M.current()) end

function M.art(max_height, quote) return require('stoa.render').art(quote or M.current(), max_height) end

function M.show() require('stoa.view').open(M.current()) end

function M.notify()
  local quote = M.current()
  vim.notify(('“%s”\n%s'):format(quote.text, M.attribution(quote)), vim.log.levels.INFO, { title = 'stoa' })
end

function M.copy()
  local quote = M.current()
  local text = ('“%s” %s'):format(quote.text, M.attribution(quote))
  vim.fn.setreg('"', text)
  pcall(vim.fn.setreg, '+', text)
  vim.notify('Quote copied', vim.log.levels.INFO, { title = 'stoa' })
end

function M.home() require('stoa.dashboard').home() end

function M.sync() require('stoa.sync').run { force = true, report = true } end

function M.info() require('stoa.sync').info() end

return M

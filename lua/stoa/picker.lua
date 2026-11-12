local config = require 'stoa.config'
local store = require 'stoa.store'

local M = {}

local seeded = false

local function random(n)
  if not seeded then
    math.randomseed(tonumber(tostring((vim.uv or vim.loop).hrtime()):sub(-9)) + vim.fn.getpid())
    for _ = 1, 5 do
      math.random()
    end
    seeded = true
  end
  return math.random(n)
end

function M.allowed(quote)
  local categories = config.options.categories
  if type(quote) ~= 'table' or type(quote.text) ~= 'string' or type(quote.id) ~= 'string' then return false end
  return not categories or vim.tbl_contains(categories, quote.category)
end

function M.resolve(quote)
  local art = store.art(quote.id) or require('stoa.generate').art(quote.id)
  return { id = quote.id, text = quote.text, author = quote.author, work = quote.work, category = quote.category, art = art }
end

function M.pick(exclude)
  local quotes = vim.tbl_filter(M.allowed, store.quotes())
  if #quotes == 0 then return nil end

  local state = store.state()
  local seen = {}
  for _, id in ipairs(state.seen or {}) do
    seen[id] = true
  end

  local pool = vim.tbl_filter(function(q) return not seen[q.id] and q.id ~= exclude end, quotes)
  local history = state.seen or {}
  if #pool == 0 then
    history = {}
    pool = vim.tbl_filter(function(q) return q.id ~= exclude end, quotes)
    if #pool == 0 then pool = quotes end
  end

  local quote = pool[random(#pool)]
  for _ = 1, 6 do
    if store.has_art(quote.id) then break end
    quote = pool[random(#pool)]
  end
  history[#history + 1] = quote.id
  store.update_state { seen = history }
  return M.resolve(quote)
end

return M

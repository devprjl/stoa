local root = vim.fs.dirname(vim.fs.dirname(vim.fs.normalize(vim.fn.fnamemodify(debug.getinfo(1, 'S').source:sub(2), ':p'))))
vim.opt.runtimepath:prepend(root)

local passed, failed = 0, 0

local function tmp()
  local dir = vim.fn.tempname()
  vim.fn.mkdir(dir, 'p')
  return dir
end

local function write(path, value)
  vim.fn.mkdir(vim.fs.dirname(path), 'p')
  local file = assert(io.open(path, 'w'))
  file:write(type(value) == 'string' and value or vim.json.encode(value))
  file:close()
end

local function pack(dir, version, count, art_hash)
  local quotes = {}
  for i = 1, count do
    quotes[i] = {
      id = ('q%d'):format(i),
      text = ('quote %d of pack %d'):format(i, version),
      author = 'Tester',
      category = i % 2 == 0 and 'game' or 'philosophy',
      art = 'bust',
    }
  end
  write(dir .. '/quotes.json', quotes)
  write(dir .. '/art/bust.json', { id = 'bust', large = { 'LARGE', 'LARGE', 'LARGE', 'LARGE' }, small = { 'SMALL' }, hash = art_hash })
  write(dir .. '/index.json', { version = version, quotes = count, updated = '2026-01-01', art = { bust = art_hash or 'a1' } })
end

local function reset(opts)
  for name in pairs(package.loaded) do
    if name:find '^stoa' then package.loaded[name] = nil end
  end
  local bundled, state, synced = tmp(), tmp(), tmp()
  pack(bundled, 1, opts and opts.count or 6)
  require('stoa').setup(vim.tbl_deep_extend('force', {
    paths = { bundled = bundled, state = state, pack = synced },
    sync = { enabled = false, urls = {} },
  }, opts and opts.config or {}))
  return { bundled = bundled, state = state, synced = synced }
end

local function test(name, fn)
  local ok, err = pcall(fn)
  if ok then
    passed = passed + 1
    print('ok    ' .. name)
  else
    failed = failed + 1
    print('FAIL  ' .. name .. '\n      ' .. tostring(err))
  end
end

local function eq(actual, expected, label)
  if not vim.deep_equal(actual, expected) then error(('%s: expected %s, got %s'):format(label or 'value', vim.inspect(expected), vim.inspect(actual)), 2) end
end

local function wait(predicate) assert(vim.wait(10000, predicate, 20), 'timed out') end

test('picker shows every quote once before repeating', function()
  reset { count = 6 }
  local picker = require 'stoa.picker'
  local seen = {}
  for _ = 1, 6 do
    local quote = picker.pick()
    assert(not seen[quote.id], 'repeated ' .. quote.id)
    seen[quote.id] = true
  end
  eq(vim.tbl_count(seen), 6, 'unique quotes')
  assert(picker.pick(), 'a new cycle starts')
end)

test('picker respects the category filter', function()
  reset { count = 8, config = { categories = { 'game' } } }
  local picker = require 'stoa.picker'
  for _ = 1, 12 do
    eq(picker.pick().category, 'game', 'category')
  end
end)

test('picked quotes carry their art', function()
  reset()
  local quote = require('stoa.picker').pick()
  eq(quote.art.small, { 'SMALL' }, 'art')
end)

test('current is stable in a session and next changes it', function()
  reset()
  local stoa = require 'stoa'
  local first = stoa.current()
  eq(stoa.current().id, first.id, 'same quote')
  assert(stoa.next().id ~= first.id, 'next gives a different quote')
end)

test('a prepared quote is used on the next start', function()
  local dirs = reset()
  local picker = require 'stoa.picker'
  local prepared = picker.pick()
  write(dirs.state .. '/next.json', prepared)
  eq(require('stoa').current().id, prepared.id, 'prepared quote')
  eq(vim.fn.filereadable(dirs.state .. '/next.json'), 0, 'prepared file consumed')
end)

test('falls back to a built-in quote with no data at all', function()
  local dirs = reset()
  vim.fn.delete(dirs.bundled, 'rf')
  local quote = require('stoa').current()
  eq(quote.id, 'fallback', 'fallback quote')
end)

test('corrupt files never raise', function()
  local dirs = reset()
  write(dirs.bundled .. '/quotes.json', '{ not json')
  write(dirs.state .. '/state.json', '[[[')
  eq(require('stoa').current().id, 'fallback', 'fallback quote')
end)

test('render picks art by height and wraps text', function()
  reset()
  local render = require 'stoa.render'
  local quote = { text = ('word '):rep(40), author = 'A', work = 'W', art = { large = { 'L', 'L', 'L', 'L' }, small = { 'S' } } }
  eq(#render.art(quote, 10), 4, 'large art')
  eq(#render.art(quote, 2), 1, 'small art')
  eq(#render.art(quote, 0), 0, 'no art')
  eq(render.attribution(quote), '— A, W', 'attribution')
  for _, line in ipairs(render.wrap(quote.text, 30)) do
    assert(#line <= 30, 'line too long')
  end
end)

test('sync installs a newer pack from a file url', function()
  local remote = tmp()
  pack(remote, 5, 9, 'b2')
  local dirs = reset { config = { sync = { enabled = true, urls = { 'file://' .. remote } } } }
  local done
  require('stoa.sync').run { on_done = function(ok) done = ok end }
  wait(function() return done ~= nil end)
  eq(done, true, 'sync result')
  eq(#require('stoa.store').quotes(), 9, 'quote count')
  eq(require('stoa.store').art('bust').hash, 'b2', 'art refreshed')
  eq(vim.fn.filereadable(dirs.synced .. '/index.json'), 1, 'index saved')
end)

test('sync skips a pack that is not newer', function()
  local remote = tmp()
  pack(remote, 1, 9)
  local dirs = reset { config = { sync = { enabled = true, urls = { 'file://' .. remote } } } }
  local done
  require('stoa.sync').run { on_done = function(ok) done = ok end }
  wait(function() return done ~= nil end)
  eq(vim.fn.filereadable(dirs.synced .. '/index.json'), 0, 'nothing downloaded')
  eq(#require('stoa.store').quotes(), 6, 'bundled quotes kept')
end)

test('sync falls through to the second url', function()
  local remote = tmp()
  pack(remote, 3, 7)
  reset { config = { sync = { enabled = true, urls = { 'file:///nonexistent/stoa', 'file://' .. remote } } } }
  local done
  require('stoa.sync').run { on_done = function(ok) done = ok end }
  wait(function() return done ~= nil end)
  eq(#require('stoa.store').quotes(), 7, 'quote count')
end)

test('a dead url leaves data untouched and stays silent', function()
  local dirs = reset { config = { sync = { enabled = true, timeout = 2, urls = { 'file:///nonexistent/stoa', 'http://127.0.0.1:9/data' } } } }
  local notified = false
  local original = vim.notify
  vim.notify = function() notified = true end
  local done
  require('stoa.sync').run { on_done = function(ok) done = ok end }
  wait(function() return done ~= nil end)
  vim.notify = original
  eq(done, false, 'sync result')
  eq(notified, false, 'no notification')
  eq(#require('stoa.store').quotes(), 6, 'bundled quotes kept')
  eq(vim.fn.filereadable(dirs.synced .. '/index.json'), 0, 'nothing written')
  assert(require('stoa.store').state().next_sync > os.time(), 'retry is scheduled')
end)

test('a broken remote pack is rejected', function()
  local remote = tmp()
  pack(remote, 9, 4)
  write(remote .. '/quotes.json', '<html>rate limited</html>')
  reset { config = { sync = { enabled = true, urls = { 'file://' .. remote } } } }
  local done
  require('stoa.sync').run { on_done = function(ok) done = ok end }
  wait(function() return done ~= nil end)
  eq(done, false, 'sync result')
  eq(#require('stoa.store').quotes(), 6, 'bundled quotes kept')
end)

test('the float opens, cycles and closes', function()
  reset()
  vim.cmd 'runtime plugin/stoa.lua'
  vim.cmd 'Stoa'
  eq(vim.bo.filetype, 'stoa', 'filetype')
  local text = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), '\n')
  assert(text:find('Tester', 1, true), 'attribution rendered')
  vim.cmd 'Stoa next'
  eq(vim.bo.filetype, 'stoa', 'still open')
  vim.api.nvim_feedkeys('q', 'x', false)
  assert(vim.bo.filetype ~= 'stoa', 'closed')
end)

test('the built-in start screen renders', function()
  reset()
  require('stoa.dashboard').open()
  eq(vim.bo.filetype, 'stoa', 'filetype')
  local text = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), '\n')
  assert(text:find 'quote %d of pack 1', 'quote rendered')
  vim.cmd 'enew'
end)

print(('\n%d passed, %d failed'):format(passed, failed))
os.exit(failed == 0 and 0 or 1)

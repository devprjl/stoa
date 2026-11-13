local config = require 'stoa.config'
local store = require 'stoa.store'

local M = {}

local running = false

local function decode(content)
  local ok, value = pcall(vim.json.decode, content, { luanil = { object = true, array = true } })
  return ok and type(value) == 'table' and value or nil
end

local function fetch(file, callback, attempt)
  attempt = attempt or 1
  local base = config.options.sync.urls[attempt]
  if not base then return callback(nil) end
  local command = { 'curl', '-fsSL', '--max-time', tostring(config.options.sync.timeout), base .. '/' .. file }
  local ok = pcall(
    vim.system,
    command,
    { text = true },
    vim.schedule_wrap(function(result)
      if result.code == 0 and result.stdout and result.stdout ~= '' then
        callback(result.stdout)
      else
        fetch(file, callback, attempt + 1)
      end
    end)
  )
  if not ok then callback(nil) end
end

local function finish(opts, ok, message)
  running = false
  local now = os.time()
  store.update_state {
    last_result = message,
    last_attempt = now,
    next_sync = now + (ok and config.options.sync.interval or math.min(3600, config.options.sync.interval)),
  }
  if opts.report then vim.notify(message, vim.log.levels.INFO, { title = 'stoa' }) end
  if opts.on_done then opts.on_done(ok, message) end
end

local function download_art(ids, done)
  local index = 0
  local function step()
    index = index + 1
    local id = ids[index]
    if not id then return done() end
    fetch('art/' .. id .. '.json', function(content)
      local art = content and decode(content)
      if art and type(art.large) == 'table' and type(art.small) == 'table' then store.write_raw(('%s/art/%s.json'):format(store.synced(), id), content) end
      step()
    end)
  end
  step()
end

local function stale_art(remote)
  local known = {}
  local bundled = store.read(store.bundled() .. '/index.json') or {}
  for id, hash in pairs(type(bundled.art) == 'table' and bundled.art or {}) do
    known[id] = hash
  end
  local synced = store.read(store.synced() .. '/index.json') or {}
  for id, hash in pairs(type(synced.art) == 'table' and synced.art or {}) do
    if vim.fn.filereadable(('%s/art/%s.json'):format(store.synced(), id)) == 1 then known[id] = hash end
  end
  local ids = {}
  for id, hash in pairs(type(remote.art) == 'table' and remote.art or {}) do
    if type(id) == 'string' and not id:find '[^%w%-_]' and known[id] ~= hash then ids[#ids + 1] = id end
  end
  table.sort(ids)
  return ids
end

function M.run(opts)
  opts = opts or {}
  if running then return end
  if vim.fn.executable 'curl' ~= 1 then return finish(opts, false, 'curl not found, using bundled quotes') end
  running = true

  fetch('index.json', function(index_content)
    local remote = index_content and decode(index_content)
    if not remote or type(remote.version) ~= 'number' then return finish(opts, false, 'offline, using local quotes') end

    local _, local_index = store.pack()
    if remote.version <= (local_index.version or 0) then return finish(opts, true, ('up to date (pack %d)'):format(local_index.version or 0)) end

    fetch('quotes.json', function(quotes_content)
      local quotes = quotes_content and decode(quotes_content)
      if not quotes or #quotes == 0 then return finish(opts, false, 'offline, using local quotes') end

      download_art(stale_art(remote), function()
        local saved = store.write_raw(store.synced() .. '/quotes.json', quotes_content) and store.write_raw(store.synced() .. '/index.json', index_content)
        if not saved then return finish(opts, false, 'could not save the new pack') end
        finish(opts, true, ('updated to pack %d (%d quotes)'):format(remote.version, #quotes))
      end)
    end)
  end)
end

function M.maybe()
  local sync = config.options.sync
  if not sync.enabled or #sync.urls == 0 then return end
  if os.time() < (store.state().next_sync or 0) then return end
  M.run()
end

function M.info()
  local dir, index = store.pack()
  local state = store.state()
  local lines = {
    ('pack %s, %s quotes, %s art pieces'):format(index.version or '?', index.quotes or '?', type(index.art) == 'table' and vim.tbl_count(index.art) or '?'),
    ('source: %s'):format(dir == store.bundled() and 'bundled with the plugin' or 'synced from GitHub'),
    ('updated: %s'):format(index.updated or 'unknown'),
    ('seen this cycle: %d'):format(#(state.seen or {})),
    ('art on screen: %s'):format((require('stoa').current().art or {}).credit or 'generated pattern'),
    ('last sync: %s'):format(state.last_attempt and (os.date('%Y-%m-%d %H:%M', state.last_attempt) .. ', ' .. (state.last_result or '')) or 'never'),
  }
  vim.notify(table.concat(lines, '\n'), vim.log.levels.INFO, { title = 'stoa' })
end

return M

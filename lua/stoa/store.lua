local config = require 'stoa.config'
local uv = vim.uv or vim.loop

local M = {}

local root = vim.fs.dirname(vim.fs.dirname(vim.fs.dirname(debug.getinfo(1, 'S').source:sub(2))))

function M.bundled() return config.options.paths.bundled or (root .. '/data') end

function M.synced() return config.options.paths.pack end

function M.state_path(name) return config.options.paths.state .. '/' .. name end

function M.read(path)
  local file = io.open(path, 'r')
  if not file then return nil end
  local content = file:read '*a'
  file:close()
  local ok, value = pcall(vim.json.decode, content, { luanil = { object = true, array = true } })
  if ok and type(value) == 'table' then return value end
  return nil
end

function M.write_raw(path, content)
  vim.fn.mkdir(vim.fs.dirname(path), 'p')
  local tmp = ('%s.%d.tmp'):format(path, uv.os_getpid())
  local file = io.open(tmp, 'w')
  if not file then return false end
  file:write(content)
  file:close()
  return uv.fs_rename(tmp, path) == true
end

function M.write(path, value) return M.write_raw(path, vim.json.encode(value)) end

function M.remove(path) uv.fs_unlink(path) end

function M.pack()
  local bundled = M.read(M.bundled() .. '/index.json')
  local synced = M.read(M.synced() .. '/index.json')
  if synced and (not bundled or (synced.version or 0) > (bundled.version or 0)) then return M.synced(), synced end
  return M.bundled(), bundled or {}
end

function M.quotes()
  local dir = M.pack()
  return M.read(dir .. '/quotes.json') or M.read(M.bundled() .. '/quotes.json') or {}
end

function M.art(id)
  if type(id) ~= 'string' or id == '' or id:find '[^%w%-_]' then return nil end
  for _, dir in ipairs { M.synced(), M.bundled() } do
    local art = M.read(('%s/art/%s.json'):format(dir, id))
    if art and type(art.large) == 'table' and type(art.small) == 'table' and #art.large > 0 then return art end
  end
  return nil
end

function M.has_art(id)
  for _, dir in ipairs { M.synced(), M.bundled() } do
    if vim.fn.filereadable(('%s/art/%s.json'):format(dir, id)) == 1 then return true end
  end
  return false
end

function M.state() return M.read(M.state_path 'state.json') or {} end

function M.update_state(changes)
  local state = vim.tbl_extend('force', M.state(), changes)
  M.write(M.state_path 'state.json', state)
  return state
end

return M

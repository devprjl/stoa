local M = {}

local bit = require 'bit'

local function rng(seed)
  local state = seed % 2147483647
  if state <= 0 then state = state + 2147483646 end
  return function()
    state = (state * 48271) % 2147483647
    return state / 2147483647
  end
end

local function canvas(columns, rows)
  local width, height = columns * 2, rows * 4
  local dots = {}
  local board = { width = width, height = height }
  function board.set(x, y)
    x, y = math.floor(x + 0.5), math.floor(y + 0.5)
    if x >= 0 and x < width and y >= 0 and y < height then dots[y * width + x] = true end
  end
  function board.lines()
    local weights = { { 0, 0, 1 }, { 0, 1, 2 }, { 0, 2, 4 }, { 1, 0, 8 }, { 1, 1, 16 }, { 1, 2, 32 }, { 0, 3, 64 }, { 1, 3, 128 } }
    local lines = {}
    for row = 0, rows - 1 do
      local cells = {}
      for column = 0, columns - 1 do
        local bits = 0
        for _, weight in ipairs(weights) do
          if dots[(row * 4 + weight[2]) * width + column * 2 + weight[1]] then bits = bits + weight[3] end
        end
        cells[#cells + 1] = string.char(0xE2, 0xA0 + bit.rshift(bits, 6), 0x80 + bit.band(bits, 63))
      end
      lines[#lines + 1] = table.concat(cells)
    end
    return lines
  end
  return board
end

local function line(board, x0, y0, x1, y1)
  local steps = math.max(math.abs(x1 - x0), math.abs(y1 - y0), 1)
  for step = 0, steps do
    board.set(x0 + (x1 - x0) * step / steps, y0 + (y1 - y0) * step / steps)
  end
end

local function circle(board, cx, cy, radius, from, to)
  local steps = math.max(12, math.floor(radius * 7))
  for step = 0, steps do
    local angle = (from or 0) + ((to or math.pi * 2) - (from or 0)) * step / steps
    board.set(cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
  end
end

local styles = {}

function styles.orbits(board, random)
  local cx, cy = board.width / 2, board.height / 2
  local reach = math.min(cx, cy) - 1
  local rings = 4 + math.floor(random() * 4)
  for ring = 1, rings do
    local radius = reach * ring / rings
    local start = random() * math.pi * 2
    circle(board, cx, cy, radius, start, start + math.pi * (0.9 + random() * 1.1))
    local angle = random() * math.pi * 2
    local px, py = cx + math.cos(angle) * radius, cy + math.sin(angle) * radius
    for dx = -1, 1 do
      for dy = -1, 1 do
        board.set(px + dx, py + dy)
      end
    end
  end
  circle(board, cx, cy, 2.5)
  circle(board, cx, cy, 1.2)
end

function styles.constellation(board, random)
  local stars = {}
  for index = 1, 9 + math.floor(random() * 6) do
    stars[index] = { 4 + random() * (board.width - 8), 4 + random() * (board.height - 8) }
  end
  table.sort(stars, function(a, b) return a[1] < b[1] end)
  for index = 1, #stars - 1 do
    if random() < 0.8 then line(board, stars[index][1], stars[index][2], stars[index + 1][1], stars[index + 1][2]) end
  end
  for _, star in ipairs(stars) do
    for _, offset in ipairs { { 0, 0 }, { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }, { 2, 0 }, { -2, 0 }, { 0, 2 }, { 0, -2 } } do
      board.set(star[1] + offset[1], star[2] + offset[2])
    end
  end
  for _ = 1, 40 do
    board.set(random() * board.width, random() * board.height)
  end
end

function styles.waves(board, random)
  local layers = 5 + math.floor(random() * 4)
  for layer = 1, layers do
    local base = board.height * layer / (layers + 1)
    local amplitude = 2 + random() * (board.height / 9)
    local frequency = 0.05 + random() * 0.1
    local phase = random() * math.pi * 2
    for x = 0, board.width - 1 do
      board.set(x, base + math.sin(x * frequency + phase) * amplitude + math.sin(x * frequency * 2.3 + phase) * amplitude * 0.3)
    end
  end
end

function styles.peaks(board, random)
  local horizon = board.height * (0.55 + random() * 0.2)
  local sun_x, sun_y, sun_r = board.width * (0.2 + random() * 0.6), board.height * (0.15 + random() * 0.2), 4 + random() * 4
  for radius = 1, sun_r do
    circle(board, sun_x, sun_y, radius)
  end
  for range = 1, 3 do
    local x, y = 0, horizon + range * 4
    while x < board.width do
      local nx = x + 6 + random() * 14
      local ny = horizon + range * 5 - random() * (board.height * 0.45) / range
      local mid = (x + nx) / 2
      line(board, x, y, mid, ny)
      line(board, mid, ny, nx, horizon + range * 4)
      x, y = nx, horizon + range * 4
    end
  end
  for x = 0, board.width - 1, 2 do
    board.set(x, board.height - 2)
  end
end

function styles.mandala(board, random)
  local cx, cy = board.width / 2, board.height / 2
  local reach = math.min(cx, cy) - 1
  local petals = 5 + math.floor(random() * 8)
  local depth = 0.25 + random() * 0.5
  local twist = random() * math.pi
  for layer = 1, 3 do
    local scale = reach * layer / 3
    local steps = 520
    for step = 0, steps do
      local angle = math.pi * 2 * step / steps
      local radius = scale * (1 - depth + depth * math.abs(math.cos(petals * angle / 2 + twist * layer)))
      board.set(cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
    end
  end
end

function styles.spiral(board, random)
  local cx, cy = board.width / 2, board.height / 2
  local reach = math.min(cx, cy) - 1
  local arms = 2 + math.floor(random() * 4)
  local turns = 1.5 + random() * 2
  for arm = 0, arms - 1 do
    local offset = math.pi * 2 * arm / arms
    for step = 0, 400 do
      local progress = step / 400
      local angle = offset + progress * turns * math.pi * 2
      board.set(cx + math.cos(angle) * reach * progress, cy + math.sin(angle) * reach * progress)
    end
  end
  circle(board, cx, cy, reach)
end

local order = { 'orbits', 'constellation', 'waves', 'peaks', 'mandala', 'spiral' }

local function seed_of(id)
  local seed = 7
  for index = 1, #id do
    seed = (seed * 31 + id:byte(index)) % 2147483647
  end
  return seed
end

local function draw(id, columns, rows)
  local seed = seed_of(id)
  local random = rng(seed)
  local board = canvas(columns, rows)
  styles[order[seed % #order + 1]](board, random)
  return board.lines()
end

function M.art(id)
  id = tostring(id or 'stoa')
  return { id = id, generated = true, large = draw(id, 44, 20), small = draw(id, 30, 13) }
end

return M

-- A shared syntax fixture, not an application service.
local retries = 3
local function greet(name)
  if name == nil then
    return "unknown"
  end
  return "hello " .. name
end
print(greet("world"), retries)

-- A policy with an explicit method table.
local Policy = {}
local policy_metatable = { __index = Policy }

function Policy.new(delays, enabled)
  return setmetatable({ delays = delays, enabled = enabled ~= false }, policy_metatable)
end

function Policy:delay(attempt)
  if not self.enabled then
    return nil, "retry disabled"
  end
  local delay = self.delays[attempt]
  if delay == nil then
    return nil, "retry budget exhausted"
  end
  return delay
end

local policy = Policy.new({ 100, 200, 400 }, true)
local attempt = ... or 2
return policy:delay(attempt)

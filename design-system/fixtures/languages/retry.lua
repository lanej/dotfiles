-- A policy with an explicit method table.
local Policy = {}
Policy.__index = Policy

function Policy.new(delays)
  return setmetatable({ delays = delays }, Policy)
end

function Policy:delay(attempt)
  return self.delays[attempt] or nil
end

local policy = Policy.new({ 100, 200, 400 })
return policy:delay(2)

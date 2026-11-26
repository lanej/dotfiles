# Keep policy values immutable.
class RetryPolicy
  def initialize(delays: [100, 200, 400])
    @delays = delays.freeze
  end

  def remaining(attempt)
    @delays.drop(attempt).map do |ms|
      { delay: ms, state: :queued, ready: false }
    end
  end

  def next_delay(attempt, enabled: true)
    return nil unless enabled

    @delays[attempt]
  end

  def describe
    "retry budget: #{@delays.size}"
  end
end

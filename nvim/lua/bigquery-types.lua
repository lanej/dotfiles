local M = {}
local reference = "https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/data-types"

local types = {
	STRING = {
		"string_type",
		"Unicode text encoded as UTF-8. STRING(L) limits length to L characters, not bytes; longer assignments raise OUT_OF_RANGE.",
	},
	BYTES = { "bytes_type", "Binary data. BYTES(L) limits length to L bytes." },
	BOOL = { "boolean_type", "Logical TRUE or FALSE." },
	INT64 = { "integer_type", "Signed 64-bit integer." },
	FLOAT64 = { "floating_point_type", "Approximate double-precision floating-point number." },
	NUMERIC = { "decimal_types", "Exact decimal with precision 38 and scale 9." },
	BIGNUMERIC = { "decimal_types", "Exact decimal with scale 38 and approximately 76.8 digits of precision." },
	DATE = { "date_type", "Calendar date without time or time zone." },
	DATETIME = { "datetime_type", "Calendar date and time without a time zone." },
	TIME = { "time_type", "Time of day without a date or time zone." },
	TIMESTAMP = { "timestamp_type", "Absolute instant with microsecond precision." },
	INTERVAL = { "interval_type", "Duration expressed in years, months, days, hours, minutes and seconds." },
	GEOGRAPHY = { "geography_type", "Points, lines and polygons on Earth's surface." },
	JSON = { "json_type", "Structured JSON data." },
	ARRAY = { "array_type", "Ordered values of one type. Directly nested arrays are unsupported." },
	STRUCT = { "struct_type", "Ordered fields, each with its own type and optional name." },
	RANGE = { "range_type", "Date, datetime or timestamp interval; lower bound inclusive, upper bound exclusive." },
}
local aliases = {
	BOOLEAN = "BOOL",
	INT = "INT64",
	SMALLINT = "INT64",
	INTEGER = "INT64",
	BIGINT = "INT64",
	TINYINT = "INT64",
	BYTEINT = "INT64",
	DECIMAL = "NUMERIC",
	BIGDECIMAL = "BIGNUMERIC",
}

function M.info(declaration)
	local word = declaration:match("^%s*([%w_]+)")
	word = word and word:upper()
	local canonical = aliases[word] or word
	local entry = types[canonical]
	if not entry then
		return
	end
	return { name = word, canonical = canonical, summary = entry[2], url = reference .. "#" .. entry[1] }
end

function M.explanation(declaration)
	local info = M.info(declaration)
	if not info then
		return
	end
	local lines = { info.summary }
	if info.canonical == "STRING" then
		local limit = declaration:match("^%s*[%w_]+%s*%(%s*(%d+)%s*%)%s*$")
		if limit then
			lines[#lines + 1] = ""
			lines[#lines + 1] = "Declared maximum: " .. limit .. " Unicode characters."
		end
	end
	lines[#lines + 1] = ""
	lines[#lines + 1] = "[GoogleSQL type reference](" .. info.url .. ")"
	return table.concat(lines, "\n")
end

function M.contents(declaration)
	local body = M.explanation(declaration)
	if body then
		return { kind = "markdown", value = "```sql\n" .. declaration .. "\n```\n\n" .. body }
	end
end
return M

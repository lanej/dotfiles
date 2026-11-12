package main

import (
	"encoding/json"
	"fmt"
	"strconv"
	"unicode/utf16"
	"unicode/utf8"
)

// gitText retains the filesystem bytes encoded by Python's surrogateescape JSON.
type gitText string

func (value gitText) MarshalJSON() ([]byte, error) {
	text := string(value)
	if utf8.ValidString(text) {
		return json.Marshal(text)
	}

	result := []byte{'"'}

	for len(text) > 0 {
		character, length := utf8.DecodeRuneInString(text)
		if character == utf8.RuneError && length == 1 {
			result = append(result, fmt.Sprintf(`\udc%02x`, text[0])...)
		} else {
			encoded, err := json.Marshal(text[:length])
			if err != nil {
				return nil, err
			}

			result = append(result, encoded[1:len(encoded)-1]...)
		}

		text = text[length:]
	}

	return append(result, '"'), nil
}

func (value *gitText) UnmarshalJSON(data []byte) error {
	var decoded string
	if err := json.Unmarshal(data, &decoded); err != nil {
		return err
	}

	result := []byte{}

	for index := 1; index < len(data)-1; index++ {
		if data[index] != '\\' {
			result = append(result, data[index])
			continue
		}

		index++
		switch data[index] {
		case '"', '\\', '/':
			result = append(result, data[index])
		case 'b':
			result = append(result, '\b')
		case 'f':
			result = append(result, '\f')
		case 'n':
			result = append(result, '\n')
		case 'r':
			result = append(result, '\r')
		case 't':
			result = append(result, '\t')
		case 'u':
			unit, err := strconv.ParseUint(string(data[index+1:index+5]), 16, 16)
			if err != nil {
				return err
			}

			index += 4

			switch {
			case unit >= 0xd800 && unit <= 0xdbff:
				if index+6 >= len(data) || data[index+1] != '\\' || data[index+2] != 'u' {
					return fmt.Errorf("invalid Unicode path surrogate")
				}

				low, err := strconv.ParseUint(string(data[index+3:index+7]), 16, 16)
				if err != nil {
					return err
				}

				if low < 0xdc00 || low > 0xdfff {
					return fmt.Errorf("invalid Unicode path surrogate")
				}

				result = utf8.AppendRune(result, utf16.DecodeRune(rune(unit), rune(low)))
				index += 6
			case unit >= 0xdc80 && unit <= 0xdcff:
				result = append(result, byte(unit-0xdc00))
			case unit >= 0xd800 && unit <= 0xdfff:
				return fmt.Errorf("unsupported Unicode path surrogate")
			default:
				result = utf8.AppendRune(result, rune(unit))
			}
		default:
			return fmt.Errorf("invalid JSON string escape")
		}
	}

	*value = gitText(result)

	return nil
}

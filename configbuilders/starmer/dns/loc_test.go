// SPDX-License-Identifier: AGPL-3.0-only

package dns

import "testing"

type packSizeTestCase struct {
	input float64
	expected uint8
}

func Test_packSizePrecision(t *testing.T) {
	cases := []packSizeTestCase{
		{0.001, 0x10},
		{0.01, 0x10},  // 10 mm, min representable value
		{0.025, 0x20},
		{1, 0x12},
		{10, 0x13},
		{20, 0x23},
		{30, 0x33},
		{100, 0x14},
		{3574, 0x35},
		{90e6, 0x99},  // 90 km, max representable value
		{1e10, 0x99},
		{1e29, 0x99},
	}
	for i, testCase := range cases {
		if got := packSizePrecision(testCase.input); got != testCase.expected {
			t.Errorf("Case #%d: expected input %.3f -> output 0x%x, got 0x%x)",
				i, testCase.input, testCase.expected, got)
		}
	}
}

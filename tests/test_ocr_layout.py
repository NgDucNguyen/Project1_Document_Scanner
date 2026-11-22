"""Kiểm tra không mất dòng, không trộn cột và không ghép sai hàng form."""
from pathlib import Path
import sys
import unittest
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/document_scanner'))
from ocr.layout import arrange_lines, apply_layout


def line(text, x, y, width=80, height=20):
    return {'text': text, 'box': [x, y, x + width, y + height]}


class LayoutTests(unittest.TestCase):
    def test_form_keeps_value_on_label_row_without_stealing_next_row(self):
        lines = [line('John Doe', 180, 0), line('Name:', 0, 0),
                 line('Age:', 0, 40), line('21', 180, 40)]
        result = arrange_lines(lines)
        self.assertEqual(result['selected_mode'], 'form')
        self.assertEqual(result['text'], 'Name: John Doe\nAge: 21')
        self.assertEqual([x['value'] for x in result['fields']], ['John Doe', '21'])

    def test_two_columns_are_read_down_each_column(self):
        lines = [line('L1', 0, 0), line('R1', 300, 0), line('L2', 0, 28),
                 line('R2', 300, 28), line('L3', 0, 56), line('R3', 300, 56)]
        self.assertEqual(arrange_lines(lines)['text'], 'L1\nL2\nL3\n\nR1\nR2\nR3')

    def test_title_above_columns_stays_before_both_columns(self):
        lines = [line('Heading', 0, 0, 400), line('L1', 0, 60),
                 line('R1', 300, 60), line('L2', 0, 90), line('R2', 300, 90)]
        self.assertEqual(arrange_lines(lines, 'columns')['text'], 'Heading\n\nL1\nL2\n\nR1\nR2')

    def test_no_lost_or_duplicated_lines_and_no_character_rewriting(self):
        lines = [line('Name:', 0, 0), line('J0hn?', 160, 0),
                 line('Name:', 0, 40), line('J0hn?', 160, 40)]
        for mode in ('auto', 'form', 'columns', 'plain'):
            result = arrange_lines(lines, mode)
            ids = [i for b in result['blocks'] for r in b['rows'] for i in r['line_ids']]
            self.assertEqual(sorted(ids), list(range(len(lines))))
            self.assertEqual(Counter(''.join(result['text'].split())),
                             Counter(''.join(x['text'] for x in lines).replace(' ', '')))

    def test_plain_keeps_raw_order_and_layout_does_not_mutate_raw_lines(self):
        lines = [line('Date:', 0, 0), line('2026', 180, 0)]
        details = {'text': 'Date:\n2026', 'lines': lines, 'warnings': []}
        result = apply_layout(details, 'form')
        self.assertEqual(result['text'], 'Date: 2026')
        self.assertEqual(result['raw_text'], details['text'])
        self.assertEqual(details['text'], 'Date:\n2026')
        self.assertEqual(arrange_lines(lines, 'plain')['text'], details['text'])

    def test_adjacent_field_labels_do_not_become_values(self):
        result = arrange_lines([line('Name:', 0, 0), line('Date:', 200, 0)], 'form')
        self.assertEqual(result['fields'], [])
        result = arrange_lines([line('Name:', 0, 0), line('Date: 2026', 200, 0)], 'form')
        self.assertEqual(len(result['fields']), 1)
        self.assertEqual(result['fields'][0]['label'], 'Date:')

    def test_inline_fields_and_empty_input(self):
        result = arrange_lines([line('Name: Jane', 0, 0), line('Date: 2026', 0, 40)])
        self.assertEqual(result['selected_mode'], 'form')
        self.assertEqual(result['fields'][0]['value'], 'Jane')
        self.assertEqual(arrange_lines([])['text'], '')


if __name__ == '__main__':
    unittest.main()

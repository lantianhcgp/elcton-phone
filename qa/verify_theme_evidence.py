#!/usr/bin/env python3
"""Cross-check actual framebuffer, hierarchy and before/after state. No green by flags alone."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import cast
import xml.etree.ElementTree as ET
from PIL import Image

LIGHT = (249, 245, 255)
DARK = (12, 15, 21)
PHASES = ('initial', 'cold-dark', 'cold-system-dark', 'cold-light-under-dark-system')
REQUIRED = (
    'r2-light-today', 'r2-light-week', 'r2-light-editor', 'r2-light-devices', 'r2-light-settings',
    'r2-light-options', 'r2-light-date-error-ime', 'r2-dark-options',
    'r2-dark-today', 'r2-dark-week', 'r2-dark-editor', 'r2-dark-devices', 'r2-dark-settings',
    'r2-dark-date-error-ime', 'r2-cold-dark', 'r2-system-light-options', 'r2-cold-system-dark',
    'r2-system-dark-today', 'r2-system-live-light-options', 'r2-explicit-light-options',
    'r2-explicit-light-under-dark-system', 'r2-cold-light-under-dark-system', 'r2-legacy-dark-selected',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def box(value):
    if isinstance(value, str):
        parsed = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', value)
        if not parsed:
            raise AssertionError('Malformed hierarchy bounds')
        value = list(map(int, parsed.groups()))
    assert isinstance(value, list) and len(value) == 4, 'Four finite bounds required'
    assert all(isinstance(n, (int, float)) for n in value), 'Non-numeric bounds'
    result = tuple(map(int, value))
    assert result[0] < result[2] and result[1] < result[3], 'Empty or inverted bounds'
    return result


def inside(rect, width, height):
    return 0 <= rect[0] < rect[2] <= width and 0 <= rect[1] < rect[3] <= height


def count_ink(image, rect, dark, step=1):
    count = 0
    for y in range(rect[1], rect[3], step):
        for x in range(rect[0], rect[2], step):
            rgb = image.getpixel((x, y))
            count += min(rgb) > 100 if dark else max(rgb) < 180
    return count


def background_probe_rows(state, height, needs_ime):
    nav_y = (int(state['navigationTop'])+int(state['navigationBottom']))//2 if needs_ime else int(state['navigationBottom'])-10
    return (10, height//3, nav_y)


def keyboard_content_bounds(state, width, height):
    raw = box(state['imeBounds'])
    assert inside(raw, width, height), 'Input method outside screenshot window'
    inset_top = height - int(state['imeBottom'])
    assert inset_top >= state['navigationBottom']-12, 'Actual keyboard inset overlaps app navigation'
    assert raw[1] <= inset_top+12, 'IME hierarchy is below the active keyboard inset'
    effective = (raw[0], max(raw[1], inset_top), raw[2], min(raw[3], height-int(state['systemNavigationHeight'])))
    assert inside(effective, width, height) and effective[3]-effective[1] > height*.14, 'Keyboard content is empty or too small'
    return effective


def inspect_capture(picture):
    picture = Path(picture)
    result = {'name': picture.stem, 'passed': False, 'errors': []}
    try:
        receipt = json.loads(picture.with_name(picture.stem+'-state.json').read_text())
        hierarchy = picture.with_suffix('.xml')
        assert receipt['pngSha256'] == sha(picture), 'PNG is not from the bound capture'
        assert receipt['xmlSha256'] == sha(hierarchy), 'XML is not from the bound capture'
        assert receipt['xmlStable'] is True and receipt['xmlBeforeSha256'] == receipt['xmlSha256'], 'Hierarchy changed across the framebuffer capture'
        assert receipt['name'] == picture.stem and receipt['captureId'], 'Wrong or unbound scene'
        assert receipt['stable'] is True and receipt['before'] == receipt['after'], 'Insets/focus/geometry changed during capture'
        assert receipt['pixelReady'] is True, 'Device did not observe a committed ready frame'
        state = receipt['after']
        dark = receipt['expectedDark']
        assert type(dark) is bool and type(receipt['requiresIme']) is bool
        assert state['mode'] in ('LIGHT', 'DARK', 'SYSTEM')
        if state['mode'] != 'SYSTEM':
            assert dark == (state['mode'] == 'DARK'), 'Explicit mode has wrong palette'
        else:
            assert dark == state['systemDark'], 'System selection has wrong palette'
        expected = DARK if dark else LIGHT
        expected_argb = -15986923 if dark else -395777
        assert state['chromeArgb'] == expected_argb, 'Wrong selected-theme system chrome'
        assert state['uiFlags'] & 8208 == (0 if dark else 8208), 'System icon polarity is wrong'
        with Image.open(picture) as source:
            image = source.convert('RGB')
        width, height = image.size
        assert (width, height) == (state['screenWidth'], state['screenHeight']), 'Wrong capture resolution'
        nav_top, nav_bottom = int(state['navigationTop']), int(state['navigationBottom'])
        assert state['statusBarHeight'] < nav_top < nav_bottom <= height, 'Navigation outside active window'
        edge = [(x, y) for y in background_probe_rows(state, height, receipt['requiresIme']) for x in (1, 2, width-3, width-2)]
        assert all(image.getpixel(p) == expected for p in edge), 'PNG palette has not caught up to theme state'
        root = ET.parse(hierarchy).getroot()
        nodes = list(root.iter('node'))
        app = [n for n in nodes if n.get('package') == 'com.hcbiu.elcton']
        assert app, 'No actual app UI in capture'
        labels = [n for n in app if n.get('text') == '今日']
        assert labels, 'Bottom navigation label missing from actual hierarchy'
        label = box(labels[0].get('bounds'))
        assert inside(label, width, height) and nav_top <= label[1] < label[3] <= nav_bottom+5
        label_ink = count_ink(image, label, dark)
        assert label_ink >= 12, 'Navigation text is not rendered'
        metrics = {'label_ink': label_ink, 'theme': state['mode'], 'expected_dark': dark,
                   'system_dark': state['systemDark'], 'pid': state['pid'], 'capture_id': receipt['captureId']}
        if receipt['requiresIme']:
            assert state['imeVisible'] is True and state['imeBottom'] > height*.14, 'Actual IME inset missing'
            ime = keyboard_content_bounds(state, width, height)
            ime_nodes = [n for n in nodes if n.get('package') == state['imePackage']]
            assert ime_nodes, 'Actual input-method hierarchy missing'
            rendered_boxes = [box(n.get('bounds')) for n in ime_nodes if n.get('bounds')]
            assert any(inside(b, width, height) and abs(b[1]-ime[1]) <= 12 and b[3] >= ime[3]-12 for b in rendered_boxes), 'IME XML and state refer to different windows'
            samples = [cast(tuple[int, int, int], image.getpixel((x, y))) for y in range(ime[1], ime[3], 4)
                       for x in range(max(ime[0], 12), min(ime[2], width-12), 4)]
            assert samples, 'IME has no framebuffer pixels'
            bright = sum(min(rgb) > 180 for rgb in samples)/len(samples)
            keyboard_ink = sum(min(rgb) < 145 for rgb in samples)
            assert bright > .45 and keyboard_ink >= 12, 'state=True but no rendered keyboard pixels'
            error = box(state['dateErrorBounds'])
            assert inside(error, width, height) and error[1] >= state['statusBarHeight'] and error[3] < nav_top, 'Date error outside keyboard-resized viewport'
            errors = [n for n in app if n.get('text') == '请输入有效日期（YYYY-MM-DD）']
            assert errors, 'Date error missing from actual hierarchy'
            xml_error = box(errors[0].get('bounds'))
            assert all(abs(a-b) <= 8 for a, b in zip(xml_error, error)), 'Date XML and state bounds disagree'
            error_ink = count_ink(image, error, dark)
            assert error_ink >= 12, 'Date error text not rendered in PNG'
            metrics.update({'ime_bounds': list(ime), 'raw_ime_bounds': state['imeBounds'], 'keyboard_bright_fraction': bright,
                            'keyboard_ink_pixels': keyboard_ink, 'date_error_bounds': list(error), 'error_ink_pixels': error_ink})
        else:
            assert state['imeVisible'] is False, 'Unexpected IME in theme screenshot'
            system_top = height - state['systemNavigationHeight']
            assert nav_bottom <= system_top+5 and 0 < state['systemNavigationHeight'] < height*.15, 'Unexpected system navigation inset'
            system_box = (12, system_top, width-12, height)
            system_ink = count_ink(image, system_box, dark, step=2)
            assert system_ink >= 24, 'System navigation keys/gesture handle not rendered with theme polarity'
            assert all(image.getpixel((x, height-8)) == expected for x in (1, 2, width-3, width-2)), 'System navigation background differs from the page'
            metrics['system_navigation_ink'] = system_ink
        result.update({'passed': True, 'metrics': metrics})
    except (AssertionError, OSError, ValueError, TypeError, KeyError) as error:
        result['errors'].append(str(error))
    return result


def verify_product(product, host):
    product = Path(product)
    reports = [inspect_capture(product/(name+'.png')) for name in REQUIRED]
    errors = [r['name']+': '+('; '.join(r['errors'])) for r in reports if not r['passed']]
    processes = {}
    for phase in PHASES:
        path = product/f'r2-{phase}-result.json'
        try:
            result = json.loads(path.read_text())
            assert result['passed'] is True and result['phase'] == phase
            processes[phase] = result['pid']
            assert result['navigationMode'] == host['navigation_mode']
            assert 'OK (1 test)' in host['phases'][phase]['stdout']
            assert host['phases'][phase]['exit_code'] == 0
        except (AssertionError, OSError, ValueError, KeyError) as error:
            errors.append(phase+': '+str(error))
    if len(set(processes.values())) != len(PHASES):
        errors.append('All four phases must run in distinct actual processes')
    for phase in PHASES[1:]:
        stop = host.get('phases', {}).get(phase, {}).get('force_stop', {})
        if stop.get('target_pid_after') != '' or stop.get('test_pid_after') != '':
            errors.append(phase+': no verified host process force-stop')
    transitions = {
        'r2-light-options': ('LIGHT', False, False),
        'r2-dark-options': ('DARK', True, False),
        'r2-cold-dark': ('DARK', True, False),
        'r2-system-light-options': ('SYSTEM', False, False),
        'r2-cold-system-dark': ('SYSTEM', True, True),
        'r2-system-live-light-options': ('SYSTEM', False, False),
        'r2-explicit-light-under-dark-system': ('LIGHT', False, True),
        'r2-cold-light-under-dark-system': ('LIGHT', False, True),
    }
    lookup = {r['name']: r for r in reports}
    for name, (mode, dark, system) in transitions.items():
        metrics = lookup[name].get('metrics', {})
        if (metrics.get('theme'), metrics.get('expected_dark'), metrics.get('system_dark')) != (mode, dark, system):
            errors.append(name+': requested user transition missing')
    return {'passed': not errors, 'source_sha': host['source_sha'], 'navigation_mode': host['navigation_mode'],
            'screenshots': len(reports), 'phase_process_ids': processes, 'errors': errors, 'scenes': reports,
            'scope': 'Actual emulator APK; independent PNG/XML/state checks; no physical paired watch'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--product', type=Path, required=True)
    parser.add_argument('--host', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = verify_product(args.product, json.loads(args.host.read_text()))
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('passed', 'navigation_mode', 'screenshots', 'errors')}))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()

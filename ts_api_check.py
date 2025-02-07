import glob
import json
import os
import re
import subprocess

path = os.path.dirname(os.path.realpath(__file__))


def ts_check():
    with open(os.path.join(path, 'tests/snapshots/check.ts'), 'w') as checkfile:
        requests = []
        responses = []
        for snapshot in glob.glob(os.path.join(path, 'tests/snapshots/*.json')):
            with open(snapshot) as snapjson:
                try:
                    shot = json.load(snapjson)
                except Exception as e:
                    print(e)
                    continue
                if 'data' in shot.get('request', {}):
                    requests.append((os.path.basename(snapshot), shot['request']))
                if (shot.get('response', {}).get('status_code', None)) not in [
                    200,
                    201,
                ]:
                    continue
                responses.append((os.path.basename(snapshot), shot['response']))

        with open(os.path.join(path, 'tests/type_template.ts')) as template:
            checkfile.write(template.read())
            checkfile.write('\n\n')
            for f, r in requests:
                checkfile.write(f'// {f}\n')
                parts = [p for p in r['url'].split('/') if p.strip()]
                if re.match(r'\d+', parts[-1]):
                    parts = parts[:-1]
                if re.match(r'feed_\w+', parts[-1]):
                    parts = parts[:-1]
                if parts[-2] == 'donations' and parts[-1] in {'flagged', 'unprocessed'}:
                    parts = parts[:-1]
                method = r['method'].lower().capitalize()
                if parts[-1][-1] == 's':
                    parts[-1] = parts[-1][:-1]
                checkfile.write(
                    f'{parts[-1]}{method} = {json.dumps(r["data"], indent=True)}\n'
                )
            checkfile.write('\n\n')
            checkfile.write(
                '\n'.join(
                    f'// {f}\nresponse = {json.dumps(r, indent=True)};'
                    for f, r in responses
                )
            )

    return subprocess.call(['yarn', 'tsc']) == 0


if __name__ == '__main__':
    assert ts_check(), 'type check failed'

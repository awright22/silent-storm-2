"""Track which game screenshots still need an adversarial review.

    python tools/reviews.py                 list screenshots with no review yet
    python tools/reviews.py --batch N       write them to build/reviews/batches/ in groups of N
    python tools/reviews.py --verdicts      summarise the reviews that exist

Rule (docs/screenshot-review.md): every screenshot of the game is reviewed by
a reviewer agent before anything is concluded from it. A screenshot is any
PNG under build/shots, build/survey/shots or docs/screenshots. Its claim is the
text file next to it, <name>.png.claim.txt, written by run.py --claim and by
survey.py. Its review is build/reviews/<folder>__<name>.png.md.

Screenshots moved to a "superseded" subfolder are retired and not listed.
A batch file holds one screenshot per block: image path, claim, review path.
Hand each batch file to one reviewer agent.
"""
import os
import re
import sys

import config

FOLDERS = ('build/shots', 'build/survey/shots', 'docs/screenshots')
REVIEWS = os.path.join(config.REPO, 'build', 'reviews')


def review_path(folder, name):
    return os.path.join(REVIEWS, '%s__%s.md' % (folder.replace('/', '_'), name))


def screenshots():
    """[(image path, claim or None, review path)] for every live screenshot."""
    found = []
    for folder in FOLDERS:
        full = os.path.join(config.REPO, *folder.split('/'))
        if not os.path.isdir(full):
            continue
        for name in sorted(os.listdir(full)):
            if not name.lower().endswith('.png'):
                continue
            image = os.path.join(full, name)
            claim_file = image + '.claim.txt'
            claim = None
            if os.path.exists(claim_file):
                with open(claim_file, encoding='utf-8') as f:
                    claim = f.read().strip()
            found.append((image, claim, review_path(folder, name)))
    return found


def write_claim(image_path, claim):
    with open(image_path + '.claim.txt', 'w', encoding='utf-8', newline='\n') as f:
        f.write(claim.strip() + '\n')


def main():
    args = sys.argv[1:]
    shots = screenshots()
    if args[:1] == ['--verdicts']:
        counts = {}
        for image, _, review in shots:
            if not os.path.exists(review):
                continue
            with open(review, encoding='utf-8', errors='replace') as f:
                match = re.search(r'^Verdict:\s*(.+)$', f.read(), re.MULTILINE)
            verdict = match.group(1).strip() if match else 'no verdict line'
            counts[verdict] = counts.get(verdict, 0) + 1
            print('%-22s %s' % (verdict, os.path.relpath(image, config.REPO)))
        print()
        for verdict, count in sorted(counts.items()):
            print('%4d  %s' % (count, verdict))
        return

    pending = [shot for shot in shots if not os.path.exists(shot[2])]
    if args[:1] == ['--batch']:
        size = int(args[1])
        folder = os.path.join(REVIEWS, 'batches')
        os.makedirs(folder, exist_ok=True)
        for old in os.listdir(folder):
            os.remove(os.path.join(folder, old))
        for n in range(0, len(pending), size):
            path = os.path.join(folder, 'batch_%03d.txt' % (n // size + 1))
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                for image, claim, review in pending[n:n + size]:
                    f.write('Screenshot: %s\nClaim: %s\nReview: %s\n\n' % (
                        image, claim or 'NO CLAIM RECORDED (say so in the review and judge the image on its own)',
                        review))
            print(path)
        return

    for image, claim, _ in pending:
        print('%s%s' % (os.path.relpath(image, config.REPO), '' if claim else '   (no claim recorded)'))
    print('%d of %d screenshots have no review' % (len(pending), len(shots)))
    sys.exit(1 if pending else 0)


if __name__ == '__main__':
    main()

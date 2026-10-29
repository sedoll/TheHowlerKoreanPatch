"""한글 패치를 되돌린다: 백업해 둔 원본 Howler.swf와 media 파일을 제자리에 복사한다."""
import os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, '..')

shutil.copyfile(os.path.join(HERE, 'Howler.swf.orig'), os.path.join(GAME, 'Howler.swf'))
orig = os.path.join(HERE, 'orig')
for root, _, files in os.walk(orig):
    for f in files:
        src = os.path.join(root, f)
        dst = os.path.join(GAME, 'media', os.path.relpath(src, orig))
        shutil.copyfile(src, dst)
print('원본으로 복원했습니다.')

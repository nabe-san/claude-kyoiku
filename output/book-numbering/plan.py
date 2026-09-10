import pathlib, json, hashlib, re
root = pathlib.Path(r'C:\Users\kengo\Desktop\MyObsidian\06_RawSources\books')
rules = [('20世紀のグローバルヒストリー',20),('わたしたちの歴史総合２',9),('わたしたちの歴史総合３',10),('わたしたちの歴史総合５',11),('アジアのナショナリズム',23),('イスラームから見た世界史',6),('ハンドブック ヨーロッパ外交史',25),('全体主義の起源',5),('危機の二十年',19),('大学の先生と学ぶ',4),('幕末維新史への招待',7),('教養のグローバルヒストリー',8),('明日のための現代史',18),('明日のための近代史',1),('歴史総合',2),('澤木興道聞き書き',17),('禅 鈴木大拙',13),('禅とはなにか',14),('禅問答入門',16),('禅談',15),('自由論',26),('陰謀論',12),('食権力の現代史',24)]
plan=[]
for p in sorted(root.glob('*.md')):
    matches=[num for prefix,num in rules if p.stem.startswith(prefix)]
    if len(matches)!=1: raise ValueError(f'Unmatched: {p.name}')
    target=p.with_name(f'{matches[0]:02d}_'+p.name)
    if target.exists(): raise FileExistsError(target)
    plan.append({'old':str(p),'new':str(target),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
pathlib.Path('output/book-numbering/rename-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(plan)} files planned')

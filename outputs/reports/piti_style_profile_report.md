# Piti Style Profile Report

- Generated at: 2026-05-19T03:01:32.657913+00:00
- Analyzed decks: 전당포 주식회사_배형찬.pptx
- Shape records: 173
- Text shape records: 130
- Slide size: {'width_in': 13.333, 'height_in': 7.5, 'width_cm': 33.867, 'height_cm': 19.05}

## Common Fonts

- none detected

## Common Font Sizes

- 28.0 pt: 111
- 20.0 pt: 12
- 54.0 pt: 4
- 32.0 pt: 1
- 52.0 pt: 1

## Common Colors

- #FF0000: 81

## Theme / Master Inheritance Signals

- likely inherited style records: 130
- font family inherited/implicit records: 130
- font size inherited/implicit records: 1
- font color inherited/implicit records: 49

## Theme / Master Font Candidates

- theme files: ['ppt/theme/theme1.xml', 'ppt/theme/theme2.xml']
- master files: ['ppt/slideMasters/slideMaster1.xml']
- layout files: 11 layout XML files
- major_latin: 맑은 고딕
- major_east_asia: 맑은 고딕
- minor_latin: 맑은 고딕
- minor_east_asia: 맑은 고딕
- resolved font candidates: ['맑은 고딕']
- renderer fallback font: 맑은 고딕
- explicit font families are sparse because most slide text inherits theme/master font references such as `+mj-ea` and `+mn-ea`.
- title style fonts/sizes: ['맑은 고딕'] / [44.0]
- body style fonts/sizes: ['맑은 고딕'] / [28.0, 24.0, 20.0, 18.0]
- other style fonts/sizes: ['맑은 고딕'] / [18.0]
- PowerPoint, Windows, and Google Slides may substitute fonts differently; visual QA is still required after renderer application.

## Layout Patterns

### big_headline

- shape_count: 6
- x/y/w/h cm median: 17.7 / 5.422 / 10.306 / 1.453
- font_size_pt_median: 28.0
- font_family_top: None
- font_color_top: #FF0000

### chart

- shape_count: 21
- x/y/w/h cm median: 1.591 / 3.229 / 31.092 / 1.453
- font_size_pt_median: 28.0
- font_family_top: None
- font_color_top: #FF0000

### checklist

- shape_count: 9
- x/y/w/h cm median: 9.71 / 8.497 / 9.399 / 1.453
- font_size_pt_median: 28.0
- font_family_top: None
- font_color_top: #FF0000

### closing

- shape_count: 2
- x/y/w/h cm median: 1.591 / 2.11 / 31.092 / 7.023
- font_size_pt_median: 28.0
- font_family_top: None
- font_color_top: #FF0000

### headline_body

- shape_count: 13
- x/y/w/h cm median: 1.591 / 3.357 / 31.092 / 3.616
- font_size_pt_median: 28.0
- font_family_top: None
- font_color_top: #FF0000

### image_heavy

- shape_count: 44
- x/y/w/h cm median: 1.591 / 2.05 / 31.092 / 2.534
- font_size_pt_median: 28.0
- font_family_top: None
- font_color_top: #FF0000

### quote

- shape_count: 30
- x/y/w/h cm median: 1.591 / 4.009 / 20.265 / 1.82
- font_size_pt_median: 28.0
- font_family_top: None
- font_color_top: #FF0000

### section_title

- shape_count: 4
- x/y/w/h cm median: 2.345 / 3.538 / 29.869 / 6.735
- font_size_pt_median: 54.0
- font_family_top: None
- font_color_top: None

### title

- shape_count: 1
- x/y/w/h cm median: 2.38 / 3.118 / 29.106 / 6.632
- font_size_pt_median: None
- font_family_top: None
- font_color_top: None

## Notes / Source Patterns

- {'notes_with_urls': 167, 'source_url_present': 167, 'image_url_present': 74}

## Piti Renderer Recommendations

- Start with `맑은 고딕` as the first explicit font candidate, while noting theme inheritance.
- Keep `Malgun Gothic` as a cross-environment fallback when the Korean theme font is unavailable.
- Use observed common font sizes as candidates: [28.0, 20.0, 54.0, 32.0, 52.0].
- title: median box x/y/w/h cm 2.38/3.118/29.106/6.632, font None pt.
- section_title: median box x/y/w/h cm 2.345/3.538/29.869/6.735, font 54.0 pt.
- headline_body: median box x/y/w/h cm 1.591/3.357/31.092/3.616, font 28.0 pt.
- image_heavy: median box x/y/w/h cm 1.591/2.05/31.092/2.534, font 28.0 pt.
- Preserve speaker notes/source labels before visual tuning.
- Do not apply image placement automatically until copyright workflow exists.

## Extraction Caveats

- Theme/master inherited font values are not fully resolved; inherited_style marks likely inherited text.
- Rendered line breaks can differ by OS font substitution and PowerPoint layout engine.
- Group shapes and complex SmartArt/chart internals are summarized at container level.
- Color values using theme scheme colors are reported as scheme:<name> unless explicit RGB is present.
- Manual visual QA is still required before applying these values to renderer output.

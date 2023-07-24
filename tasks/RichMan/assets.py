from module.atom.image import RuleImage
from module.atom.click import RuleClick
from module.atom.long_click import RuleLongClick
from module.atom.swipe import RuleSwipe
from module.atom.ocr import RuleOcr
from module.atom.list import RuleList

# This file was automatically generated by ./dev_tools/assets_extract.py.
# Don't modify it manually.
class RichManAssets: 


	# Image Rule Assets
	# 千物宝库 
	I_TT_ENTER = RuleImage(roi_front=(1140,585,73,76), roi_back=(1140,585,73,76), threshold=0.8, method="Template matching", file="./tasks/RichMan/tt/tt_tt_enter.png")
	# 确认进入 
	I_TT_CHECK = RuleImage(roi_front=(141,61,228,67), roi_back=(141,61,228,67), threshold=0.8, method="Template matching", file="./tasks/RichMan/tt/tt_tt_check.png")
	# description 
	I_TT_BLACK = RuleImage(roi_front=(710,176,91,90), roi_back=(453,171,589,109), threshold=0.8, method="Template matching", file="./tasks/RichMan/tt/tt_tt_black.png")
	# description 
	I_TT_TICKET_BULE = RuleImage(roi_front=(484,176,85,91), roi_back=(475,170,562,110), threshold=0.8, method="Template matching", file="./tasks/RichMan/tt/tt_tt_ticket_bule.png")
	# description 
	I_TT_AP = RuleImage(roi_front=(938,177,88,87), roi_back=(467,167,581,123), threshold=0.8, method="Template matching", file="./tasks/RichMan/tt/tt_tt_ap.png")
	# 提高 
	I_TT_BUY_UP = RuleImage(roi_front=(761,411,59,57), roi_back=(761,411,59,57), threshold=0.8, method="Template matching", file="./tasks/RichMan/tt/tt_tt_buy_up.png")
	# description 
	I_TT_BUY_CONFIRM = RuleImage(roi_front=(584,512,53,53), roi_back=(553,508,169,60), threshold=0.8, method="Template matching", file="./tasks/RichMan/tt/tt_tt_buy_confirm.png")


	# Ocr Rule Assets
	# Ocr-description 
	O_TT_TOTOL = RuleOcr(roi=(1121,10,116,35), area=(1121,10,116,35), mode="Digit", method="Default", keyword="", name="tt_totol")
	# Ocr-description 
	O_TT_BLUE_TICKET = RuleOcr(roi=(509,307,531,92), area=(509,307,531,92), mode="Full", method="Default", keyword="2000", name="tt_blue_ticket")
	# Ocr-description 
	O_TT_BLACK = RuleOcr(roi=(498,313,528,89), area=(498,313,528,89), mode="Full", method="Default", keyword="350", name="tt_black")
	# Ocr-description 
	O_TT_AP = RuleOcr(roi=(502,311,535,91), area=(502,311,535,91), mode="Full", method="Default", keyword="300", name="tt_ap")
	# Ocr-description 
	O_TT_BUY = RuleOcr(roi=(602,509,104,61), area=(602,509,104,61), mode="Full", method="Default", keyword="", name="tt_buy")
	# Ocr-description 
	O_TT_NUMBER = RuleOcr(roi=(576,415,58,49), area=(576,415,58,49), mode="Digit", method="Default", keyword="", name="tt_number")


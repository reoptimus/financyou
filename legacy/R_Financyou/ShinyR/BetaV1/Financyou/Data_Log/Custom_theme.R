# palette
# hclwizard.org:64230/hclwizard
# HUE 1 : 271
# HUE2 : 84
# CHROMA1 : 72
# CHROMA2 : 100
color0<-"rgb(0,50,100)"
color1<-"rgb(0,112,189)" #blue nuit
color2<-"rgb(0,193,229)" #blue ciel
color3<-"rgba(44,222,235,1)" #turquoise
color4<-"rgb(200,250,250)" # white-blue
color5<-"rgb(255,255,255)" # blanc
colorGrad<-cssGradientThreeColors(
  direction = "down"
  ,colorStart = color5 #"rgb(0,50,100)"
  ,colorMiddle = color1 #"rgba(44,222,235,1)"
  ,colorEnd = color2 #"rgba(0,255,213,1)"
  ,colorStartPos = 0
  ,colorMiddlePos = 60
  ,colorEndPos = 100)

## Custom color palette
# sequential_hcl(n = 4, h = c(244, 161), c = c(84, NA, 7), l = c(44, 95), power = c(0.25, 1.85), register = "FinancYou_palette")

theme_blue_gradient_custom <- shinyDashboardThemeDIY(
  
  ### general
  appFontFamily = "Arial"
  ,appFontColor = "rgb(0,0,0)"
  ,primaryFontColor = "rgb(0,0,0)"
  ,infoFontColor = "rgb(0,0,0)"
  ,successFontColor = "rgb(0,0,0)"
  ,warningFontColor = "rgb(0,0,0)"
  ,dangerFontColor = "rgb(0,0,0)"
  ,bodyBackColor = colorGrad
  
  ### header
  ,logoBackColor = color5 #colorGrad 
  
  ,headerButtonBackColor = color0 #"rgb(238,238,238)"
  ,headerButtonIconColor = "rgb(238,238,238)" # "rgb(0,0,0)" #"rgb(75,75,75)"
  ,headerButtonBackColorHover = "rgb(210,210,210)"
  ,headerButtonIconColorHover = "rgb(0,0,0)"
  
  ,headerBackColor = color0 #"rgb(20,97,117)"
  ,headerBoxShadowColor = "#aaaaaa"
  ,headerBoxShadowSize = "2px 2px 2px"
  
  ### sidebar
  ,sidebarBackColor = color0 #"rgb(20,97,117)"

  ,sidebarPadding = 0
  
  ,sidebarMenuBackColor = "transparent"
  ,sidebarMenuPadding = 0
  ,sidebarMenuBorderRadius = 0
  
  ,sidebarShadowRadius = "3px 5px 5px"
  ,sidebarShadowColor = "#aaaaaa"
  
  ,sidebarUserTextColor = "rgb(255,255,255)"
  
  ,sidebarSearchBackColor = color1 #"rgb(55,72,80)"
  ,sidebarSearchIconColor = color2 #"rgb(153,153,153)"
  ,sidebarSearchBorderColor = color3 #"rgb(55,72,80)"
  
  ,sidebarTabTextColor = "rgb(255,255,255)"
  ,sidebarTabTextSize = 13
  ,sidebarTabBorderStyle = "none none solid none"
  ,sidebarTabBorderColor = "rgb(35,106,135)"
  ,sidebarTabBorderWidth = 1
  
  ,sidebarTabBackColorSelected = cssGradientThreeColors(
    direction = "right"
    ,colorStart = color1 #"rgba(44,222,235,1)"
    ,colorMiddle = color3 #"rgba(44,222,235,1)"
    ,colorEnd = color1 #"rgba(0,255,213,1)"
    ,colorStartPos = 0
    ,colorMiddlePos = 30
    ,colorEndPos = 100
  )
  ,sidebarTabTextColorSelected = "rgb(0,0,0)"
  ,sidebarTabRadiusSelected = "0px 20px 20px 0px"
  
  ,sidebarTabBackColorHover = cssGradientThreeColors(
    direction = "right"
    ,colorStart = "rgba(44,222,235,1)"
    ,colorMiddle = "rgba(44,222,235,1)"
    ,colorEnd = "rgba(0,255,213,1)"
    ,colorStartPos = 0
    ,colorMiddlePos = 30
    ,colorEndPos = 100
  )
  ,sidebarTabTextColorHover = "rgb(50,50,50)"
  ,sidebarTabBorderStyleHover = "none none solid none"
  ,sidebarTabBorderColorHover = "rgb(75,126,151)"
  ,sidebarTabBorderWidthHover = 1
  ,sidebarTabRadiusHover = "0px 20px 20px 0px"
  
  ### boxes
  ,boxBackColor = "rgb(255,255,255)"
  ,boxBorderRadius = 5
  ,boxShadowSize = "0px 1px 1px"
  ,boxShadowColor = "rgba(0,0,0,.1)"
  ,boxTitleSize = 14
  ,boxDefaultColor = "rgb(210,214,220)"
  ,boxPrimaryColor = color2 #"rgba(44,222,235,1)"
  ,boxInfoColor = color1 #"rgb(210,214,220)"
  ,boxSuccessColor = color3 #"rgba(0,255,213,1)"
  ,boxWarningColor = color4 #"rgb(244,156,104)"
  ,boxDangerColor = "rgb(255,88,55)"
  
  ,tabBoxTabColor = "rgb(255,255,255)"
  ,tabBoxTabTextSize = 13
  ,tabBoxTabTextColor = "rgb(0,0,0)"
  ,tabBoxTabTextColorSelected = "rgb(0,0,0)"
  ,tabBoxBackColor = "rgb(255,255,255)"
  ,tabBoxHighlightColor = "rgba(44,222,235,1)"
  ,tabBoxBorderRadius = 5
  
  ### inputs
  ,buttonBackColor = "rgb(245,245,245)"
  ,buttonTextColor = "rgb(0,0,0)"
  ,buttonBorderColor = "rgb(200,200,200)"
  ,buttonBorderRadius = 5
  
  ,buttonBackColorHover = "rgb(235,235,235)"
  ,buttonTextColorHover = "rgb(100,100,100)"
  ,buttonBorderColorHover = "rgb(200,200,200)"
  
  ,textboxBackColor = "rgb(255,255,255)"
  ,textboxBorderColor = "rgb(200,200,200)"
  ,textboxBorderRadius = 5
  ,textboxBackColorSelect = "rgb(245,245,245)"
  ,textboxBorderColorSelect = "rgb(200,200,200)"
  
  ### tables
  ,tableBackColor = "rgb(255,255,255)"
  ,tableBorderColor = "rgb(240,240,240)"
  ,tableBorderTopSize = 1
  ,tableBorderRowSize = 1
  
)

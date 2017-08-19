local modpath = "/mods/additionalCameraStuff/"
local camera = import(modpath..'modules/ACScamera.lua')
local prefsUI = import(modpath..'modules/ACSprefsUI.lua')

local UIUtil = import('/lua/ui/uiutil.lua')
local LayoutHelpers = import('/lua/maui/layouthelpers.lua')
local GameMain = import('/lua/ui/game/gamemain.lua')
local Group = import('/lua/maui/group.lua').Group
local Button = import('/lua/maui/button.lua').Button
local Checkbox = import('/lua/maui/checkbox.lua').Checkbox
local Movie = import('/lua/maui/movie.lua').Movie
local Bitmap = import('/lua/maui/bitmap.lua').Bitmap
local GameCommon = import('/lua/ui/game/gamecommon.lua')
local Tooltip = import('/lua/ui/game/tooltip.lua')

local size
controls = {
    groups = {},
}

function init(mapGroup, maxSize)
    size = maxSize
    import(modpath.."modules/ACScamera.lua").addPositionChangeObserver(import(modpath.."modules/ACSUI.lua").onCameraPositionsChanged)
    createUI(mapGroup)
end


function onCameraPositionsChanged(positions)
    for i = 1, size do
        if positions[i] == nil then
            controls.groups[i] = nil
        else
            local bg = Bitmap(controls.container, UIUtil.SkinnableFile('/game/avatar/avatar-control-group_bmp.dds'))
            local savedIndex = i

            bg.icon = Bitmap(bg)
            bg.icon.Width:Set(28)
            bg.icon.Height:Set(20)
            bg.icon:SetTexture(modpath..'/textures/icon.png')
            LayoutHelpers.AtCenterIn(bg.icon, bg, 0, -4)

            bg.label = UIUtil.CreateText(bg.icon, i, 18, UIUtil.bodyFont)
            bg.label:SetColor('ffffffff')
            bg.label:SetDropShadow(true)
            LayoutHelpers.AtRightIn(bg.label, bg.icon)
            LayoutHelpers.AtBottomIn(bg.label, bg, 5)

            bg.icon:DisableHitTest()
            bg.label:DisableHitTest()

            bg.HandleEvent = function(self,event)
                if event.Type == 'ButtonPress' or event.Type == 'ButtonDClick' then
                    camera.restoreCameraPosition(savedIndex)
                end
            end

            controls.groups[i] = bg
        end
    end
    LayoutGroups()
end


function createUI(mapGroup)
    controls.parent = GetFrame(0)
    
    controls.container = Group(controls.parent)
    controls.container.Depth:Set(100)
    controls.bgTop = Bitmap(controls.container)
    controls.bgBottom = Bitmap(controls.container)
    controls.bgStretch = Bitmap(controls.container)
    controls.collapseArrow = Checkbox(controls.parent)
    
    controls.collapseArrow.OnCheck = function(self, checked)
        ToggleCameraGroups(checked)
    end
    Tooltip.AddCheckboxTooltip(controls.collapseArrow, {
        text = "[Hide/Show] Camera Positions",
        body = "Added by Additional Camera Stuff",
    })
    
    controls.container:DisableHitTest(true)
    
    controls.settingsButton = Button(controls.container,
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_over.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_down.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_over.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_dis.dds'))    
    controls.settingsButton.OnClick = function(self)
        prefsUI.createPrefsUi()
    end
    Tooltip.AddButtonTooltip(controls.settingsButton, {
        text = "Open mod settings",
        body = "",
    })

    controls.collapseArrow:Hide()
    controls.container:Hide()
    SetLayout()
end


function ToggleCameraGroups(state)
    --disable when in Screen Capture mode
    if import('/lua/ui/game/gamemain.lua').gameUIHidden then
        return
    end
    if state or controls.container:IsHidden() then
        controls.container:Show()
        controls.collapseArrow:SetCheck(true, true)
    else
        controls.container:Hide()
        controls.collapseArrow:SetCheck(false, true)
    end
end


function SetLayout()
    controls.bgTop:SetTexture(UIUtil.UIFile('/game/bracket-right/bracket_bmp_t.dds'))
    controls.bgStretch:SetTexture(UIUtil.UIFile('/game/bracket-right/bracket_bmp_m.dds'))
    controls.bgBottom:SetTexture(UIUtil.UIFile('/game/bracket-right/bracket_bmp_b.dds'))
    
    LayoutHelpers.AtRightIn(controls.bgTop, controls.container)
    LayoutHelpers.AtRightIn(controls.bgBottom, controls.container)
    
    controls.bgTop.Bottom:Set(function() return controls.container.Top() + 70 end)
    controls.bgBottom.Top:Set(function() return math.max(controls.bgTop.Bottom(), controls.container.Bottom()-20) end)
    controls.bgStretch.Top:Set(controls.bgTop.Bottom)
    controls.bgStretch.Bottom:Set(controls.bgBottom.Top)
    controls.bgStretch.Right:Set(function() return controls.bgTop.Right() - 7 end)
    
    controls.container.Height:Set(20)
    controls.container.Width:Set(60)
    LayoutHelpers.AtTopIn(controls.container, controls.parent, 638)
    LayoutHelpers.AtRightIn(controls.container, controls.parent)
    
    LayoutHelpers.AtTopIn(controls.collapseArrow, controls.container, 22)
    LayoutHelpers.AtRightIn(controls.collapseArrow, controls.parent, -3)
    
    controls.collapseArrow.Depth:Set(function() return controls.bgTop.Depth() + 1 end)
    controls.collapseArrow:SetTexture(UIUtil.UIFile('/game/tab-r-btn/tab-close_btn_up.dds'))
    controls.collapseArrow:SetNewTextures(UIUtil.UIFile('/game/tab-r-btn/tab-close_btn_up.dds'),
        UIUtil.UIFile('/game/tab-r-btn/tab-open_btn_up.dds'),
        UIUtil.UIFile('/game/tab-r-btn/tab-close_btn_over.dds'),
        UIUtil.UIFile('/game/tab-r-btn/tab-open_btn_over.dds'),
        UIUtil.UIFile('/game/tab-r-btn/tab-close_btn_dis.dds'),
        UIUtil.UIFile('/game/tab-r-btn/tab-open_btn_dis.dds'))

    LayoutHelpers.AtTopIn(controls.settingsButton, controls.container, 50)
    LayoutHelpers.AtRightIn(controls.settingsButton, controls.parent, -5)

    controls.settingsButton:SetTexture(UIUtil.SkinnableFile('/game/menu-btns/config_btn_over.dds'))
    controls.settingsButton.Depth:Set(function() return controls.bgTop.Depth() + 2 end)
    controls.settingsButton:SetNewTextures(
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_over.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_down.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_over.dds'),
        UIUtil.SkinnableFile('/game/menu-btns/config_btn_dis.dds'))
end


function LayoutGroups()
    local prevControl = false
    local firstControlTop = 0
    for i = 1, size do
        if not controls.groups[i] then
            continue
        end
        local control = controls.groups[i]
        if prevControl then
            LayoutHelpers.Below(control, prevControl, -8)
        else
            LayoutHelpers.AtTopIn(control, controls.container, 10)
            LayoutHelpers.AtRightIn(control, controls.container, 15)
            firstControlTop = control.Top()
        end
        prevControl = control
    end
    if controls.groups and table.getsize(controls.groups) > 0 then
        controls.container.Bottom:Set(prevControl.Bottom)
        controls.container:Show()
        controls.collapseArrow:Show()
    else
        controls.container.Height:Set(20)
        controls.container:Hide()
        controls.collapseArrow:Hide()
    end
end
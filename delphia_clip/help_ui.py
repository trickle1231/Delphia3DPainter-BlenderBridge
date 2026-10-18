# SPDX-License-Identifier: GPL-3.0-or-later
import bpy

TEXT = {
    'EN': [
        ('1. Send a model', ['Select meshes → Copy to Delphia.', 'In Delphia: File → Open → Open by BlenderClip.']),
        ('2. Bring textures back', ['In Delphia: Copy to Blender for the current canvas,', 'or Copy Selected to Blender in the image export dialog.', 'In Blender: Update Textures from Delphia.', 'Check the target materials and confirm.']),
        ('3. Save', ['Textures are packed automatically. Save your .blend.', 'Keep Delphia open until textures have been imported.']),
    ],
    'JP': [
        ('1. モデルを送る', ['メッシュを選択 → Copy to Delphia。', 'Delphia：ファイル → 開く → BlenderClipから開く。']),
        ('2. テクスチャを戻す', ['DelphiaのCopy to Blenderで現在のキャンバスを送信。', '複数の場合は画像書き出し画面で選択して送信します。', 'Blender：Update Textures from Delphia。', '対象マテリアルを確認して確定します。']),
        ('3. 保存する', ['画像は自動でパックされます。.blendを保存してください。', '読み込みが終わるまでDelphiaを閉じないでください。']),
    ],
    'KR': [
        ('1. 모델 보내기', ['메시 선택 → Copy to Delphia.', 'Delphia: 파일 → 열기 → BlenderClip으로 열기.']),
        ('2. 텍스처 가져오기', ['Delphia의 Copy to Blender로 현재 캔버스를 복사합니다.', '여러 캔버스는 이미지 내보내기 창에서 선택해 보냅니다.', 'Blender: Update Textures from Delphia.', '대상 머티리얼을 확인하고 적용합니다.']),
        ('3. 저장하기', ['이미지는 자동 패킹됩니다. .blend 파일을 저장하세요.', '가져오기가 끝날 때까지 Delphia를 종료하지 마세요.']),
    ],
}


class DELPHIA_OT_help(bpy.types.Operator):
    bl_idname = 'delphia.bridge_help'
    bl_label = 'Delphia Bridge Help'
    language: bpy.props.EnumProperty(items=[('EN', 'EN', 'English'), ('JP', 'JP', '日本語'), ('KR', 'KR', '한국어')], default='EN')

    def invoke(self, context, event):
        locale = bpy.context.preferences.view.language
        self.language = 'KR' if locale.startswith('ko') else 'JP' if locale.startswith('ja') else 'EN'
        return context.window_manager.invoke_props_dialog(self, width=620)

    def draw(self, context):
        self.layout.prop(self, 'language', expand=True)
        for title, lines in TEXT[self.language]:
            box = self.layout.box().column()
            box.label(text=title, translate=False)
            for line in lines:
                box.label(text=line, translate=False)
        self.layout.operator('wm.url_open', text='Delphia 3D Painter Site Link',
                             icon='URL').url = 'https://delphia3dpainter.com/'

    def execute(self, context):
        return {'FINISHED'}

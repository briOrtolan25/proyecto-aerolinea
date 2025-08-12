def __init__(self, *args, usuario=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.usuario = usuario

    vuelo_id = None
    if 'vuelo' in self.data:
        try:
            vuelo_id = int(self.data.get('vuelo'))
        except (ValueError, TypeError):
            vuelo_id = None

    if vuelo_id:
        self.fields['asiento'].queryset = Asiento.objects.filter(
            vuelo_id=vuelo_id,
            estado=Asiento.Estado.DISPONIBLE
        )
    else:
        self.fields['asiento'].queryset = Asiento.objects.none()


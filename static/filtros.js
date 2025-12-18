document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.filtro-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();

            const filtro = btn.closest('.filtro');

            document.querySelectorAll('.filtro').forEach(f => {
                if (f !== filtro) f.classList.remove('active');
            });

            filtro.classList.toggle('active');
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.filtro').forEach(f => {
            f.classList.remove('active');
        });
    });
});

export function DashboardTiles({ counts }) {
  return (
    <>
      <Tile label="Orders to pack" value={counts.toPack} to="/admin/orders?status=paid" />
      <Tile label="Refunds waiting for review" value={counts.refundsRequested} to="/admin/refunds?status=requested" />
    </>
  );
}
